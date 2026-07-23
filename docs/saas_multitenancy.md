# 🏢 Enterprise SaaS Multi-Tenancy & Tenant Lifecycle Isolation Architecture

The Collaborative Fraud Intelligence (CFI) platform operates as a multi-tenant SaaS and enterprise on-premise framework providing hard database schema isolation, context-routed session management, and per-institution cryptographic key paths.

---

## 🔒 Multi-Tenant Data Isolation Strategy

Data isolation is enforced at the database engine level to comply with SOC 2 Type II, PCI-DSS, and European Banking Secrecy laws:

1. **Context-Driven Session Routing**:
   - The `active_tenant` ContextVar determines which database engine and session factory is loaded for the active request.
   - When `active_tenant.get()` is `"bank_a"`, all ORM queries and commits execute strictly against Bank A's isolated database instance (`storage/cfi_bank_a.db` or PostgreSQL schema `tenant_bank_a.*`).

2. **Automated Tenant Provisioning**:
   - `TenantProvisioner` automates new institution onboarding (`provision_tenant("bank_d", "Delta Regional Bank")`).
   - Executes DDL schema table migrations (`Base.metadata.create_all`) for the new tenant database engine, registers the tenant in `VALID_TENANTS`, and updates state from `PROVISIONING` to `ACTIVE`.

3. **Tenant Lifecycle State Machine**:
   - `PROVISIONING`: Database schema being created.
   - `ACTIVE`: Fully operational bank node participating in FL rounds.
   - `SUSPENDED`: Temporarily blocked due to policy/compliance review.
   - `DELETED`: Soft or hard purged from network.

---

## 🛠️ Developer Code Example

```python
from app.infrastructure.database import active_tenant
from app.infrastructure.database.tenant_provisioner import TenantProvisioner

# 1. Onboard a new bank node
provisioner = TenantProvisioner()
tenant_record = await provisioner.provision_tenant("bank_d", "Delta Regional Bank")
print("Provisioned:", tenant_record.name, tenant_record.status)

# 2. Execute tenant-isolated operation
token = active_tenant.set("bank_d")
try:
    # Operations here automatically execute against bank_d DB
    pass
finally:
    active_tenant.reset(token)
```
