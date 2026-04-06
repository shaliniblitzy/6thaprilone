"""
Blitzy Platform API Test Suite - Test Package

Contains pytest test modules for validating the percent_complete field
across three Blitzy Platform API endpoints:

- GET /runs/metering — Historical run metering data
- GET /runs/metering/current — Active run metering data
- GET /project — Project details with inline metering

Test categories:
- Endpoint-specific validation (field presence, type, range)
- Cross-API consistency checks
- Edge case and boundary condition tests
"""
