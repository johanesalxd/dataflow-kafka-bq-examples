package com.johanesalxd.transforms;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

public class SqlQueryReader {

    /**
     * Reads a SQL query from a file in the classpath.
     *
     * @param fileName The name of the SQL file (e.g., "user_event_aggregations.sql")
     * @return The SQL query as a string
     * @throws RuntimeException if the file cannot be read
     */
    public static String readQuery(String fileName) {
        try (InputStream inputStream = SqlQueryReader.class.getClassLoader()
                .getResourceAsStream("udf/" + fileName)) {

            if (inputStream == null) {
                throw new RuntimeException("SQL file not found: udf/" + fileName);
            }

            return new String(inputStream.readAllBytes(), StandardCharsets.UTF_8).trim();
        } catch (IOException e) {
            throw new RuntimeException("Failed to read SQL file: udf/" + fileName, e);
        }
    }
}
