# Functional Definition — ATK Hotel QMS/MIS Overhaul

## Module Objective
To transform the `atk_hotel` module into a production-grade, enterprise-ready hospitality management system that adheres to ISO 9001 quality standards and provides real-time MIS insights for management.

## Business Scope
- **Guest Lifecycle Management**: From booking to check-out and review.
- **Room & Resource Control**: Inventory, cleaning, and maintenance.
- **Financial Integrity**: Automated Folio creation, deposit handling, and revenue tracking.
- **Quality Assurance**: Room inspections, nonconformity handling, and guest feedback loops.
- **Management Reporting**: Real-time KPI dashboards and performance trends.

## In-Scope
- Refined state machine with approval controls.
- Dedicated user roles (Receptionist, Manager, Cleaning Lead).
- Automated KPI engine for MIS reporting.
- Compliance tracking (Passport/Visa/Signature).
- Integration with Loyalty and QMS Mixins.

## Out-of-Scope
- Payroll and HR employee management (uses standard Odoo HR).
- Direct hardware integration with door locks (handled via external API).

## Process Owner
- Hotel Operations Manager.

## Stakeholders
- **Front Office**: For daily booking and guest handling.
- **Housekeeping**: For room readiness and inspection.
- **Finance**: For revenue audit and invoicing.
- **Guests**: For booking and feedback.

## Integration Points
- `sale_management`: Folio and sales tracking.
- `account`: Invoicing and payments.
- `maintenance`: Room repair requests.
- `atk_prop_mgmt`: Property-level configuration.
- `website`: Online booking engine.
