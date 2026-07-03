def pre_init_hook(cr):
    """Ensure custom columns exist in res_partner before the registry is loaded."""
    for column, definition in (
        ("first_name", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS first_name varchar"),
        ("middle_name", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS middle_name varchar"),
        ("last_name", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS last_name varchar"),
        ("is_hotel_customer", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_hotel_customer boolean DEFAULT false"),
        ("is_vip", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_vip boolean DEFAULT false"),
        ("is_foreigner", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_foreigner boolean DEFAULT false"),
        ("is_doctor", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_doctor boolean DEFAULT false"),
        ("is_single_lady", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_single_lady boolean DEFAULT false"),
        ("receives_daily_intel_report", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS receives_daily_intel_report boolean DEFAULT false"),
    ):
        cr.execute(definition)


def post_init_hook(env):
    sale_report = env.ref('sale.report_saleorder_document', raise_if_not_found=False)
    if not sale_report:
        return
    invalid_views = env['ir.ui.view'].search([
        ('inherit_id', '=', sale_report.id),
        ('arch_db', 'ilike', '/t/t/div/div[3]/div[2]')
    ])
    if invalid_views:
        invalid_views.unlink()
