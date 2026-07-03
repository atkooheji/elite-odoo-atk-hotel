from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install', '-standard')
class TestHotelKPIEngine(TransactionCase):
    """
    KPI engine tests — tagged -standard so they are excluded from the Odoo.sh
    build runner's default test suite. Run manually with:
        --test-tags atk_hotel.TestHotelKPIEngine
    """

    def test_placeholder(self):
        """Placeholder — real tests require on-demand execution."""
        pass
