from behave import given, when, then
import logging

# Reuse previous helper functions and configurations

@when('the full data pipeline is executed')
def step_when_full_pipeline_executed(context):
    # Step 1: Data Validation
    context.execute_steps('''
        When the data validation process is executed
    ''')
    if context.validation_errors:
        logging.info(f"Validation errors: {context.validation_errors}")
        # Depending on business logic, decide whether to proceed or skip invalid rows
        # For this example, we'll proceed with valid data only

    # Step 2: Data Transformation
    context.execute_steps('''
        When the conversion process is triggered
    ''')

    # Step 3: Data Loading
    context.execute_steps('''
        When the data loading process is executed
    ''')

@then('invalid data is logged and skipped, while valid data is processed and loaded')
def step_then_invalid_data_handled(context):
    # Verify that invalid data was logged
    assert context.validation_errors, "Invalid data was not logged."

    # Verify that only valid data is in Redshift
    conn = psycopg2.connect(**redshift_config)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM public.my_table;")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    # Assuming we know how many valid rows there should be
    expected_valid_rows = 2  # Adjust based on your test data
    assert count == expected_valid_rows, f"Expected {expected_valid_rows} rows, found {count}."

@then('the data is available in Redshift with accurate records')
def step_then_data_available_in_redshift(context):
    # Reuse verification from previous steps
    context.execute_steps('''
        Then the data is accurately loaded into the Redshift table "public.my_table"
    ''')
