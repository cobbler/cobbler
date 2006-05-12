import sys
import unittest

from koan import koan

class Basic(unittest.TestCase):
    """
    Koan is very network, system, and configuration dependant, so there isn't a *ton* of things that can
    be added here.  But things *should* be added.
    """
    def setUp(self):
       pass

    def tearDown(self):
       pass

    def test_basicCli(self):
       koan.main()
       assert true # didn't choke

if __name__ == "__main__":
    unittest.main(argv=sys.argv)

