## Changelog

### 1.0.0 (2025-11-18)

- Complete rewrite using pyserial instead of gammu
- Proper s6-overlay support with bashio
- Event-based SMS sending (`legacy_gsm_sms_send`)
- Minimal permissions (only `uart: true`)
- Fixed modem stability issues
- SMS reading temporarily disabled (will use +CMTI in future)
