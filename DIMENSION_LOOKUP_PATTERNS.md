# Dimension Lookup Patterns in Apache Beam Streaming Pipelines

## Business Scenario

Imagine an **e-commerce platform** that processes real-time user events (clicks, purchases, views) and needs to enrich them with user profile information for analytics and personalization.

### Data Sources:
- **Streaming Events**: User interactions from Kafka (high volume, real-time)
- **User Profiles**: Dimension table in BigQuery (slowly changing, complete dataset)
- **Product Catalog**: Product updates from Kafka (medium volume, real-time)

### Challenge:
How do you efficiently join streaming events with dimension data while balancing:
- **Data Freshness**: How quickly new/updated profiles are available
- **Performance**: Latency and throughput requirements
- **Cost**: Memory usage and BigQuery API calls
- **Complexity**: Implementation and maintenance overhead

---

## Pattern Comparison Overview

| Pattern | Data Freshness | Memory Usage | Latency | BigQuery Calls | Beam SQL Support | Complexity |
|---------|---------------|--------------|---------|----------------|------------------|------------|
| **Static Side Input** | Pipeline startup only | High | Low | 1 (startup) | Partial | Low |
| **Periodic Refresh** | Every X minutes | High | Low | Every X minutes | Partial | Medium |
| **Stream-to-Stream Join** | Real-time | Very High | Low | 1 (startup) | Full | Low |
| **Hybrid Approach** | Real-time | Medium | Low | 1 (startup) | Partial/Full | High |
| **External Lookups** | Real-time | Low | High | Per element | Partial | Medium |
| **Stateful Cache** | Real-time | Medium | Low | Configurable | Partial | High |

---

## Pattern 1: Static Side Input (Current Implementation)

### Description
Load the complete dimension table once at pipeline startup and use it as a side input for enrichment.

### Architecture
```
BigQuery (User Profiles) ──┐
                           ├─► Side Input ──┐
Kafka (Events) ────────────┼─────────────────┼─► Enriched Events
                           │                 │
Kafka (Products) ──────────┘                 │
                                            │
                           DoFn Enrichment ──┘
```

### Implementation
```java
// Read user profiles from BigQuery as side input
// Note: Using default method (not DIRECT_READ) for streaming pipeline compatibility
PCollectionView<Map<String, Row>> userProfilesView = p
    .apply("ReadUserProfilesFromBQ", BigQueryIO.readTableRows()
        .from(options.getUserProfilesTable()))
    .apply("ConvertBQToUserProfileRow", ParDo.of(new TableRowToUserProfileRow()))
    .setRowSchema(TableRowToUserProfileRow.SCHEMA)
    .apply("KeyUserProfilesByUserId", WithKeys.of((Row row) -> row.getString("user_id")))
    .setCoder(KvCoder.of(StringUtf8Coder.of(), RowCoder.of(TableRowToUserProfileRow.SCHEMA)))
    .apply("CreateUserProfileView", View.asMap());

// Use side input in enrichment
.apply("EnrichWithUserProfiles", ParDo.of(new EnrichWithUserProfileDoFn(userProfilesView))
    .withSideInputs(userProfilesView))
```

### Important Note: BigQuery Storage API Compatibility
⚠️ **Streaming Pipeline Limitation**: Do not use `BigQueryIO.TypedRead.Method.DIRECT_READ` in streaming pipelines when creating side inputs. The BigQuery Storage API requires sources to be split before reading, which is incompatible with streaming side input patterns. This will result in:
```
java.lang.UnsupportedOperationException: BigQuery storage source must be split before reading
```
Use the default BigQuery API method instead for streaming pipelines.

### Pros
- ✅ Simple implementation
- ✅ Low latency for lookups
- ✅ Single BigQuery read at startup
- ✅ Works well for stable dimension data

### Cons
- ❌ No updates after pipeline starts
- ❌ High memory usage for large dimensions
- ❌ New profiles unavailable until pipeline restart
- ❌ Cannot use Beam SQL for profile joins

### When to Use
- Dimension data changes infrequently
- Pipeline restarts are acceptable for updates
- Memory can accommodate full dimension table
- Simple implementation is preferred

---

## Pattern 2: Periodic Refresh Side Input

### Description
Refresh the side input periodically to pick up new dimension data while maintaining the lookup pattern.

### Architecture
```
BigQuery (User Profiles) ──┐ (Every 30 min)
                           ├─► Refreshing Side Input ──┐
Kafka (Events) ────────────┼─────────────────────────────┼─► Enriched Events
                           │                             │
Kafka (Products) ──────────┘                             │
                                                        │
                           DoFn Enrichment ──────────────┘
```

### Implementation
```java
// Periodic trigger for BigQuery reads
PCollectionView<Map<String, Row>> userProfilesView = p
    .apply("PeriodicTrigger",
        GenerateSequence.from(0)
            .withRate(1, Duration.standardMinutes(30)))
    .apply("ReadUserProfilesFromBQ",
        ParDo.of(new PeriodicBigQueryReader(options.getUserProfilesTable())))
    .apply("WindowForSideInput",
        Window.<Row>into(new GlobalWindows())
            .triggering(Repeatedly.forever(
                AfterProcessingTime.pastFirstElementInPane()
                    .plusDelayOf(Duration.standardMinutes(30))))
            .discardingFiredPanes())
    .apply("KeyUserProfilesByUserId", WithKeys.of((Row row) -> row.getString("user_id")))
    .setCoder(KvCoder.of(StringUtf8Coder.of(), RowCoder.of(TableRowToUserProfileRow.SCHEMA)))
    .apply("CreateUserProfileView", View.asMap());
```

### Pros
- ✅ Automatic updates without pipeline restart
- ✅ Configurable refresh interval
- ✅ Low latency for lookups
- ✅ Complete dimension table available

### Cons
- ❌ Still has update delay (refresh interval)
- ❌ High memory usage
- ❌ Regular BigQuery reads (cost)
- ❌ Complex windowing and triggering logic

### When to Use
- Dimension data changes moderately (hourly/daily)
- Some delay in updates is acceptable
- Want to avoid pipeline restarts
- Memory can accommodate full dimension table

---

## Pattern 3: Stream-to-Stream Join with Beam SQL

### Description
Convert dimension data to a stream and use Beam SQL for joining all streams together.

### Architecture
```
BigQuery (User Profiles) ──┐
                           ├─► Stream ──┐
Kafka (Events) ────────────┼────────────┼─► Beam SQL Join ──► Enriched Events
                           │            │
Kafka (Products) ──────────┘            │
                                       │
Kafka (Profile Updates) ───────────────┘
```

### Implementation
```java
// Convert BigQuery to stream
PCollection<Row> userProfilesFromBQ = p
    .apply("ReadUserProfilesFromBQ", BigQueryIO.readTableRows()...)
    .apply("ConvertToRow", ParDo.of(new TableRowToUserProfileRow()))
    .setRowSchema(UserProfileSchema.SCHEMA);

// Real-time profile updates
PCollection<Row> userProfileUpdatesFromKafka = p
    .apply("ReadProfileUpdatesFromKafka", KafkaIO...)
    .apply("ParseToRow", ParDo.of(new UserProfileToRow()))
    .setRowSchema(UserProfileSchema.SCHEMA);

// Combine and deduplicate profiles
PCollection<Row> allUserProfiles = PCollectionList
    .of(userProfilesFromBQ)
    .and(userProfileUpdatesFromKafka)
    .apply(Flatten.pCollections())
    .apply("DeduplicateProfiles", SqlTransform.query(
        "SELECT user_id, MAX(username) as username, MAX(user_segment) as user_segment, " +
        "MAX(registration_date) as registration_date, MAX(timestamp) as timestamp " +
        "FROM PCOLLECTION GROUP BY user_id"));

// SQL join all streams
PCollectionTuple inputs = PCollectionTuple
    .of(new TupleTag<>("user_events"), userEvents)
    .and(new TupleTag<>("product_updates"), productUpdates)
    .and(new TupleTag<>("user_profiles"), allUserProfiles);

PCollection<Row> enrichedEvents = inputs.apply(SqlTransform.query(
    "SELECT e.*, p.product_name, p.category, u.username, u.user_segment " +
    "FROM user_events e " +
    "LEFT JOIN product_updates p ON e.product_id = p.product_id " +
    "LEFT JOIN user_profiles u ON e.user_id = u.user_id"));
```

### Pros
- ✅ Full Beam SQL support for all joins
- ✅ Real-time updates from Kafka
- ✅ Clean, declarative SQL syntax
- ✅ Automatic deduplication handling

### Cons
- ❌ Very high memory usage (all data in streams)
- ❌ Complex windowing for stream joins
- ❌ Potential data skew issues
- ❌ Higher computational overhead

### When to Use
- Full SQL expressiveness is required
- Real-time updates are critical
- Dimension table is relatively small
- Team prefers SQL over procedural code

---

## Pattern 4: Hybrid Approach (BigQuery + Kafka)

### Description
Combine initial BigQuery load with real-time Kafka updates using stateful processing.

### Architecture
```
BigQuery (User Profiles) ──┐ (Initial Load)
                           ├─► Stateful DoFn ──┐
Kafka (Events) ────────────┼────────────────────┼─► Enriched Events
                           │                    │
Kafka (Profile Updates) ───┼────────────────────┘
                           │
Kafka (Products) ──────────┘
```

### Implementation
```java
// Initial BigQuery load as side input
PCollectionView<Map<String, Row>> initialProfilesView = // ... BigQuery read

// Real-time profile updates
PCollection<KV<String, Row>> profileUpdates = p
    .apply("ReadProfileUpdatesFromKafka", KafkaIO...)
    .apply("KeyByUserId", WithKeys.of(row -> row.getString("user_id")));

// Stateful enrichment combining both sources
.apply("EnrichWithHybridProfiles",
    ParDo.of(new StatefulProfileEnrichmentDoFn(initialProfilesView))
        .withSideInputs(initialProfilesView))

// StatefulProfileEnrichmentDoFn implementation
public class StatefulProfileEnrichmentDoFn extends DoFn<Row, Row> {
    @StateId("profileCache")
    private final StateSpec<ValueState<Row>> profileCacheSpec =
        StateSpecs.value(RowCoder.of(UserProfileSchema.SCHEMA));

    @ProcessElement
    public void processElement(
        ProcessContext c,
        @StateId("profileCache") ValueState<Row> profileCache) {

        String userId = c.element().getString("user_id");

        // Check cache first, then side input, then default
        Row profile = profileCache.read();
        if (profile == null) {
            profile = c.sideInput(initialProfilesView).get(userId);
        }

        // Enrich and output
        Row enriched = enrichWithProfile(c.element(), profile);
        c.output(enriched);
    }
}
```

### Pros
- ✅ Real-time updates with complete historical data
- ✅ Moderate memory usage (stateful caching)
- ✅ Best of both worlds approach
- ✅ Handles missing profiles gracefully

### Cons
- ❌ Complex stateful processing logic
- ❌ State management overhead
- ❌ Difficult to debug and test
- ❌ Requires careful state cleanup

### When to Use
- Need both historical completeness and real-time updates
- Can handle implementation complexity
- Memory usage needs to be controlled
- High data quality requirements

---

## Pattern 5: BigQuery External Lookups

### Description
Perform direct BigQuery lookups for each element without caching, ensuring always-fresh data.

### Architecture
```
Kafka (Events) ────────────┐
                           ├─► DoFn with BQ Client ──► Enriched Events
Kafka (Products) ──────────┘           │
                                      │
BigQuery (User Profiles) ──────────────┘ (Per-element lookup)
```

### Implementation
```java
public class BigQueryLookupDoFn extends DoFn<Row, Row> {
    private transient BigQuery bigQueryClient;
    private final String userProfilesTable;

    public BigQueryLookupDoFn(String userProfilesTable) {
        this.userProfilesTable = userProfilesTable;
    }

    @Setup
    public void setup() {
        this.bigQueryClient = BigQueryOptions.getDefaultInstance().getService();
    }

    @ProcessElement
    public void processElement(ProcessContext c) {
        String userId = c.element().getString("user_id");

        // Direct BigQuery lookup
        String query = String.format(
            "SELECT user_id, username, user_segment, registration_date " +
            "FROM `%s` WHERE user_id = '%s' LIMIT 1",
            userProfilesTable, userId);

        try {
            TableResult result = bigQueryClient.query(QueryJobConfiguration.of(query));
            Row userProfile = null;

            for (FieldValueList row : result.iterateAll()) {
                userProfile = Row.withSchema(UserProfileSchema.SCHEMA)
                    .addValue(row.get("user_id").getStringValue())
                    .addValue(row.get("username").getStringValue())
                    .addValue(row.get("user_segment").getStringValue())
                    .addValue(row.get("registration_date").getStringValue())
                    .build();
                break;
            }

            // Enrich and output
            Row enriched = enrichWithProfile(c.element(), userProfile);
            c.output(enriched);

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("BigQuery lookup interrupted", e);
        }
    }

    private Row enrichWithProfile(Row event, Row profile) {
        // Enrichment logic here
        return Row.withSchema(EnrichedEventSchema.SCHEMA)
            .addValues(event.getValues())
            .addValues(profile != null ? profile.getValues() : getDefaultProfileValues())
            .build();
    }
}

// Usage
.apply("EnrichWithBigQueryLookup", ParDo.of(new BigQueryLookupDoFn(userProfilesTable)))
```

### Pros
- ✅ Always gets the latest data
- ✅ Very low memory usage
- ✅ Simple to understand and implement
- ✅ No state management complexity
- ✅ Handles missing profiles gracefully

### Cons
- ❌ High latency per element (BigQuery roundtrip)
- ❌ Expensive (BigQuery API calls per element)
- ❌ Not suitable for high-throughput scenarios
- ❌ BigQuery quota limitations
- ❌ Network dependency for each lookup

### When to Use
- Low to medium throughput scenarios
- Always-fresh data is critical
- Memory constraints are severe
- Simple implementation is preferred
- Cost of BigQuery calls is acceptable

---

## Pattern 6: Stateful Cache with TTL

### Description
Implement a stateful cache with time-to-live (TTL) that refreshes entries as needed.

### Architecture
```
Kafka (Events) ────────────┐
                           ├─► Stateful DoFn with Cache ──► Enriched Events
Kafka (Products) ──────────┘           │
                                      │
BigQuery (User Profiles) ──────────────┘ (On cache miss)
```

### Implementation
```java
public class CachedLookupDoFn extends DoFn<Row, Row> {
    private transient BigQuery bigQueryClient;
    private final String userProfilesTable;
    private final Duration cacheTtl;

    @StateId("profileCache")
    private final StateSpec<ValueState<Row>> profileCacheSpec =
        StateSpecs.value(RowCoder.of(UserProfileSchema.SCHEMA));

    @StateId("cacheTimestamp")
    private final StateSpec<ValueState<Instant>> timestampSpec =
        StateSpecs.value(InstantCoder.of());

    @TimerId("cacheCleaner")
    private final TimerSpec cacheCleanerSpec = TimerSpecs.timer(TimeDomain.PROCESSING_TIME);

    @ProcessElement
    public void processElement(
        ProcessContext c,
        @StateId("profileCache") ValueState<Row> profileCache,
        @StateId("cacheTimestamp") ValueState<Instant> cacheTimestamp,
        @TimerId("cacheCleaner") Timer cacheCleanerTimer) {

        String userId = c.element().getString("user_id");
        Instant now = Instant.now();

        // Check if cached data is still valid
        Row cachedProfile = profileCache.read();
        Instant cachedTime = cacheTimestamp.read();

        boolean cacheValid = cachedProfile != null &&
                           cachedTime != null &&
                           now.isBefore(cachedTime.plus(cacheTtl));

        Row profile;
        if (cacheValid) {
            profile = cachedProfile;
        } else {
            // Cache miss - fetch from BigQuery
            profile = lookupFromBigQuery(userId);
            if (profile != null) {
                profileCache.write(profile);
                cacheTimestamp.write(now);
                cacheCleanerTimer.set(now.plus(cacheTtl));
            }
        }

        // Enrich and output
        Row enriched = enrichWithProfile(c.element(), profile);
        c.output(enriched);
    }

    @OnTimer("cacheCleaner")
    public void onCacheCleanup(
        @StateId("profileCache") ValueState<Row> profileCache,
        @StateId("cacheTimestamp") ValueState<Instant> cacheTimestamp) {
        // Clear expired cache
        profileCache.clear();
        cacheTimestamp.clear();
    }
}
```

### Pros
- ✅ Balanced memory usage and freshness
- ✅ Configurable cache TTL
- ✅ Reduces BigQuery API calls
- ✅ Good performance for repeated lookups
- ✅ Automatic cache cleanup

### Cons
- ❌ Complex stateful processing
- ❌ Still has some lookup latency
- ❌ Cache management overhead
- ❌ Difficult to tune TTL correctly

### When to Use
- Need balance between freshness and performance
- Moderate throughput with repeated user lookups
- Can handle stateful processing complexity
- Want to minimize BigQuery costs

---

## Decision Matrix

### Choose Based on Your Requirements:

#### **Data Freshness Priority**
- **Real-time required**: Stream-to-Stream Join, Hybrid Approach, External Lookups
- **Minutes delay acceptable**: Periodic Refresh, Stateful Cache
- **Hours/days delay acceptable**: Static Side Input

#### **Memory Constraints**
- **Severe memory limits**: External Lookups, Stateful Cache
- **Moderate memory available**: Hybrid Approach, Stateful Cache
- **High memory available**: Static Side Input, Periodic Refresh, Stream-to-Stream Join

#### **Throughput Requirements**
- **High throughput (>10K events/sec)**: Static Side Input, Periodic Refresh, Hybrid Approach
- **Medium throughput (1K-10K events/sec)**: Stateful Cache, Stream-to-Stream Join
- **Low throughput (<1K events/sec)**: External Lookups

#### **Implementation Complexity Tolerance**
- **Simple preferred**: Static Side Input, External Lookups, Stream-to-Stream Join
- **Medium complexity acceptable**: Periodic Refresh, Stateful Cache
- **High complexity acceptable**: Hybrid Approach

#### **Cost Sensitivity**
- **Cost-sensitive**: Static Side Input, Periodic Refresh, Hybrid Approach
- **Cost-moderate**: Stateful Cache, Stream-to-Stream Join
- **Cost-tolerant**: External Lookups

---

## Best Practices

### General Guidelines
1. **Start Simple**: Begin with Static Side Input and evolve as requirements change
2. **Monitor Memory**: Use Dataflow monitoring to track memory usage patterns
3. **Test Thoroughly**: Each pattern has different failure modes and edge cases
4. **Consider Data Skew**: Some patterns are more sensitive to hot keys than others
5. **Plan for Growth**: Consider how each pattern scales with data volume

### Performance Optimization
- Use appropriate coders for better serialization performance
- Consider data partitioning strategies for large dimension tables
- Implement proper error handling and retry logic
- Monitor BigQuery quotas and costs
- Use appropriate windowing strategies for stream joins

### Monitoring and Alerting
- Track lookup success/failure rates
- Monitor cache hit rates (for cached patterns)
- Alert on BigQuery quota usage
- Monitor memory usage and GC patterns
- Track end-to-end latency metrics

---

## Conclusion

The choice of dimension lookup pattern significantly impacts your streaming pipeline's performance, cost, and maintainability. Consider your specific requirements for data freshness, throughput, memory constraints, and implementation complexity when selecting the appropriate pattern.

Remember that you can also combine patterns - for example, using Static Side Input for stable dimensions and External Lookups for frequently changing ones, or implementing a fallback strategy where cached lookups fall back to external lookups on cache misses.

The key is to start with the simplest pattern that meets your requirements and evolve as your needs become more sophisticated.
