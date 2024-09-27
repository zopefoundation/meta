##############################################################################
#
# Copyright (c) 2024 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import unittest


class ConfigPackageTests(unittest.TestCase):

    def test_prepend_space(self):
        from zope.meta.config_package import prepend_space

        self.assertIsNone(prepend_space(None))
        self.assertEqual('', prepend_space(''))
        self.assertEqual(' foobar', prepend_space('foobar'))
