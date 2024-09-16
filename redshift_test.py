# File: features/steps/redshift_steps.py

from behave import given, when, then
import time

@given('the Redshift table "{table_name}" exists')
def step_impl(context, table_name):
    context.cursor.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}')")
    assert context.cursor.fetchone()[0], f"Table {table_name} does not exist"

@when('I query the table "{table_name}"')
def step_impl(context, table_name):
    context.cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
    context.result = context.cursor.fetchone()

@then('the query should return results')
def step_impl(context):
    assert context.result is not None, "Query returned no results"

@then('the column "{column_name}" in table "{table_name}" should not contain null values')
def step_impl(context, column_name, table_name):
    context.cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL")
    null_count = context.cursor.fetchone()[0]
    assert null_count == 0, f"Column {column_name} contains {null_count} null values"

@then('the row count of table "{table_name}" should match the source count of {expected_count:d}')
def step_impl(context, table_name, expected_count):
    context.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    actual_count = context.cursor.fetchone()[0]
    assert actual_count == expected_count, f"Row count mismatch. Expected {expected_count}, got {actual_count}"

@when('I execute the query "{query}"')
def step_impl(context, query):
    start_time = time.time()
    context.cursor.execute(query)
    end_time = time.time()
    context.query_time = end_time - start_time

@then('the query execution time should be less than {max_time:f} seconds')
def step_impl(context, max_time):
    assert context.query_time < max_time, f"Query took {context.query_time} seconds, which is more than the maximum allowed time of {max_time} seconds"

# File: features/redshift_tests.feature

Feature: Redshift Table Testing

  Scenario: Verify table existence and data
    Given the Redshift table "example_table" exists
    When I query the table "example_table"
    Then the query should return results

  Scenario: Check for null values in critical column
    Given the Redshift table "customer_data" exists
    Then the column "customer_id" in table "customer_data" should not contain null values

  Scenario: Verify row count matches source data
    Given the Redshift table "sales_data" exists
    Then the row count of table "sales_data" should match the source count of 10000

  Scenario: Check query performance
    When I execute the query "SELECT * FROM large_table WHERE date > '2023-01-01'"
    Then the query execution time should be less than 5.0 seconds
