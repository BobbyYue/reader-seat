"""Synthetic structural records only; never a semantic-quality verdict."""
import defensive_expression as defensive


def structural_defensive(text, profile='functional'):
    record = defensive.template(text, profile)
    record['whole_text_review'] = 'STRUCTURAL FIXTURE: current supplied surface only, no semantic acceptance claim.'
    for entry in record['items']:
        entry.update(classification='retain', reason='STRUCTURAL FIXTURE: exact-text binding test.',
                     reader_effect='STRUCTURAL FIXTURE: reader-effect field.',
                     protected_meaning='STRUCTURAL FIXTURE: meaning field.',
                     prior_context='STRUCTURAL FIXTURE: earlier-context field.',
                     direct_alternative=entry['quote'])
    return record
