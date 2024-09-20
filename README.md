# File: features/data_validation.feature

Feature: Verify data consistency between stage and dimension tables
  As a data engineer
  I want to ensure all records for a specific business date in the stage table are present in the final dimension table
  So that our data is consistent and accurate

  Scenario: All stage table records for a business date are present in the final dimension table
    Given the stage table "<stage_table>" has records for business date "<business_date>"
    When I compare the records in the stage table "<stage_table>" to the final dimension table "<dim_table>"
    Then all stage table records should be present in the final dimension table

  Examples:
    | business_date | stage_table | dim_table |
    | 2024-09-20    | STAGE_CUSTOMER | DIM_CUSTOMER |
    | 2024-09-20    | STAGE_PRODUCT  | DIM_PRODUCT  |

# File: features/steps/data_validation_steps.py

from behave import given, when, then
from datetime import datetime
import your_data_validation_module  # Replace with your actual module

@given('the stage table "{stage_table}" has records for business date "{business_date}"')
def step_given_stage_records(context, stage_table, business_date):
    context.business_date = datetime.strptime(business_date, "%Y-%m-%d")
    context.stage_table = stage_table
    context.stage_records = your_data_validation_module.get_stage_records(context.stage_table, context.business_date)
    assert len(context.stage_records) > 0, f"No records found in {stage_table} for business date {business_date}"
    print(f"Found {len(context.stage_records)} records in {stage_table} for business date {business_date}")

@when('I compare the records in the stage table "{stage_table}" to the final dimension table "{dim_table}"')
def step_when_compare_records(context, stage_table, dim_table):
    context.dim_table = dim_table
    context.dim_records = your_data_validation_module.get_dim_records(context.dim_table, context.business_date)
    print(f"Found {len(context.dim_records)} records in {dim_table} for business date {context.business_date}")

@then('all stage table records should be present in the final dimension table')
def step_then_verify_records(context):
    missing_records = []
    for record in context.stage_records:
        if record not in context.dim_records:
            missing_records.append(record)
    
    assert len(missing_records) == 0, f"{len(missing_records)} records from {context.stage_table} not found in {context.dim_table}"
    print(f"All {len(context.stage_records)} records from {context.stage_table} are present in {context.dim_table}")
