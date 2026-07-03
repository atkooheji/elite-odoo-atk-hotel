# Audit Website 2 branding and layout
w2 = env['website'].browse(2)
print(f"\n--- WEBSITE 2: {w2.name} ---")
print(f"Company: {w2.company_id.name} (ID: {w2.company_id.id})")
print(f"Menu: {w2.menu_id.name} (ID: {w2.menu_id.id})")
if w2.menu_id:
    print(f"Menu Children: {[m.name for m in w2.menu_id.child_id]}")

# 2. Check Logo specifically
company = w2.company_id
has_logo = bool(company.logo)
print(f"Company has logo: {has_logo}")

# 3. Check for Navbar Overrides
navbar_views = env['ir.ui.view'].search([
    ('name', 'ilike', 'navbar'),
    ('active', '=', True)
])
print("\n--- NAVBAR OVERRIDES ---")
for v in navbar_views:
    ext_id = v.get_external_id().get(v.id)
    site = v.website_id.name or "ALL"
    print(f"ID: {v.id} | Name: {v.name} | Site: {site} | Source: {ext_id or 'CUSTOM'}")

# 4. Check for any view hiding the menu or altering branding
suspicious_views = env['ir.ui.view'].search([
    ('active', '=', True),
    '|', '|',
    ('arch_db', 'ilike', 'o_main_nav'),
    ('arch_db', 'ilike', 'display: none'),
    ('arch_db', 'ilike', 'Elite Sports')
])
print("\n--- SUSPICIOUS VIEWS (potentially hiding/forcing branding) ---")
for v in suspicious_views:
    ext_id = v.get_external_id().get(v.id)
    if not ext_id or 'studio' in (ext_id or '').lower():
         print(f"ID: {v.id} | Name: {v.name} | Site: {v.website_id.name or 'ALL'} | ID: {ext_id}")

# 5. Check the specific menu for Website 2
if w2.menu_id:
    print(f"\nMenu {w2.menu_id.id} details:")
    for child in w2.menu_id.child_id:
        print(f"  - {child.name} (URL: {child.url})")
