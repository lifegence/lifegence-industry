# Lifegence Industry

Industry-specific modules for [Frappe](https://frappeframework.com/) / [ERPNext](https://erpnext.com/).

Provides medical receipt processing, international trade management, and voice-based mind analysis capabilities.

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

### Mind Analyzer (マインド分析)
Voice-based psychological analysis for workplace well-being.
- Real-time voice analysis sessions
- Individual and meeting analysis modes
- Trigger detection (silence spikes, speech rate changes, power imbalance, etc.)
- Automatic stale session cleanup

## Prerequisites

- Python 3.14+
- Frappe Framework v16+
- ERPNext v16+

## Installation

```bash
bench get-app https://github.com/lifegence/lifegence-industry.git
bench --site your-site install-app lifegence_industry
```

## After Installation

Run migrations to set up fixtures:

```bash
bench --site your-site migrate
```

## License

MIT - see [LICENSE](LICENSE)

## Contributing

Contributions are welcome. Please open an issue or pull request on [GitHub](https://github.com/lifegence/lifegence-industry).
