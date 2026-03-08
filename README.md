# Lifegence Industry

Industry-specific modules for [Frappe](https://frappeframework.com/) / [ERPNext](https://erpnext.com/).

Provides medical receipt processing and international trade management.

## Migrated Modules

> **Note**: The following module has been extracted to a dedicated app:
> - **Mind Analyzer (マインド分析)** → [lifegence_agent](https://github.com/lifegence/lifegence-agent) (private)

## Modules

### Medical Receipt (レセプト)
Medical receipt (診療報酬明細書) processing for healthcare facilities.
- Patient encounter fee calculation
- Monthly receipt generation with deadline reminders
- Medical receipt settings management

### Trade Management (貿易管理)
International trade and logistics management.
- Import/export document management
- ETA alerts and LC (Letter of Credit) expiry tracking
- Integration with Sales Orders, Purchase Orders, Delivery Notes, and Purchase Receipts
- Custom fields for trade-specific data

## Prerequisites

- Python 3.14+
- Frappe Framework v16+
- ERPNext v16+

## Installation

```bash
bench get-app https://github.com/lifegence/lifegence-industry.git
bench --site your-site install-app lifegence_industry
bench --site your-site migrate
```

## License

MIT - see [LICENSE](LICENSE)

## Contributing

Contributions are welcome. Please open an issue or pull request on [GitHub](https://github.com/lifegence/lifegence-industry).
