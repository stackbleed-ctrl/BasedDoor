from custom_components.baseddoor.capabilities import CapabilityReport


def test_capability_operating_modes():
    assert CapabilityReport(
        True, True, True, True, True, True, True, True
    ).operating_mode == "local_ai"

    assert CapabilityReport(
        False, False, True, True, False, False, False, True
    ).operating_mode == "deterministic_voice"

    assert CapabilityReport(
        True, True, False, False, True, False, False, True
    ).operating_mode == "observe_notify"

    assert CapabilityReport(
        False, False, False, False, False, False, False, True
    ).operating_mode == "manual_only"


def test_recording_is_fail_closed():
    report = CapabilityReport(
        True, True, True, True, True, True, True, True
    )
    assert report.recording_confirmed is False
