from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install', '-standard')
class TestAIIntegration(TransactionCase):
    """
    AI integration tests — tagged -standard so they are excluded from the Odoo.sh
    build runner's default test suite. Run manually with:
        --test-tags atk_hotel.TestAIIntegration
    """

    def test_placeholder(self):
        """Placeholder — real tests require API keys not available in CI."""
        pass
