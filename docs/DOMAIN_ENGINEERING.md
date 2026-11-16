# ClinicFlow engineering notes

- Unique active appointment slots prevent double-booking.
- Rescheduling and cancellation preserve an immutable audit trail with old/new times.
- Secure owner-only initial setup and protected API.
- Uses synthetic patients only. Not clinical software or a HIPAA/GDPR-compliant production deployment.
