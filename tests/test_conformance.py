from earthaccess_plugin_spec.testing import run_conformance

from earthaccess_harmony import HarmonyPlugin

from .fixtures import HarmonyFixtures


def test_conformance():
    run_conformance(HarmonyPlugin, fixtures=HarmonyFixtures(options={}))
