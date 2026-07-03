import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """
    Nuke corrupted footer views and their data references to break the ParseError loop.
    This runs BEFORE the XML files are loaded.
    """
    _logger.info("🛠️ [atk_hotel] PRE-MIGRATION: Nuking corrupted view registry entries...")
    
    # 1. Delete by XML ID from ir_model_data
    cr.execute("""
        DELETE FROM ir_model_data 
        WHERE module = 'atk_hotel' 
        AND name IN ('hotel_footer', 'hotel_footer_v2', 'hotel_footer_alfaris', 'hotel_footer_alfaris_v4', 'atk_hotel_footer_final_v5')
    """)
    
    # 2. Delete by Name (Planning Frontend Layout)
    cr.execute("DELETE FROM ir_ui_view WHERE name = 'Planning Frontend Layout'")
    
    # 3. Delete any view inheriting website.layout that mentions our footer ID in its arch
    # In Odoo 19, arch_db is a translated field (often jsonb), so we cast to text for LIKE
    cr.execute("""
        DELETE FROM ir_ui_view 
        WHERE inherit_id IN (
            SELECT res_id FROM ir_model_data 
            WHERE module = 'website' AND name = 'layout'
        )
        AND arch_db::text LIKE '%hotel_footer%'
    """)
    
    cr.commit()
    _logger.info("✅ [atk_hotel] PRE-MIGRATION: View registry cleaned.")
