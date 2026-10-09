const DEPRECATION = 'Roles are deprecated. Projects are the unit, and the active project is kept in the session, not in Roles/current_role.md. Use /project. Old role files under Roles/ are historical; read bSmart_Protocols/roles-and-concurrency.md before treating them as state.';

export function execute() {
  return { status: 'ok', deprecated: true, diagnostic: DEPRECATION };
}

export function migrateLegacyState() {
  return {
    status: 'ok',
    deprecated: true,
    diagnostic: 'Role migration no longer writes a role file. Run bsmart-instance-upgrade, which backs up Roles/ and merges handoffs into the matching project.',
  };
}
