def test_letter_dry_run():
    from src.tools.write_letter import write_application_letter
    letter = write_application_letter(pov="Agents are changing everything.", dry_run=True)
    assert isinstance(letter, str)
    assert len(letter) > 100
