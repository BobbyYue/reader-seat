"""Synthetic record builder for schema tests only; never a semantic verdict."""
import context_value
import source_attribution


def structural_attribution(text, source='', mode='reader', profile='functional'):
    result = source_attribution.template(text, source, mode, profile)
    result['whole_text_scan'] = 'STRUCTURAL FIXTURE; not source or reader validation'
    for item in result['items']:
        item.update(kind='unknown', speaker='unknown', speaker_basis='', support_quote='', source_scope='unresolved',
                    negative_status='unconfirmed', basis='STRUCTURAL FIXTURE, not a semantic judgment', status='pass')
    return result


def structural_context(text, profile='functional'):
    result = context_value.template(text, profile)
    result['attribution_replay'] = structural_attribution(text, profile=profile)
    result.update(audience='STRUCTURAL FIXTURE reader', purpose='Test binding only',
                  whole_text_scan='STRUCTURAL FIXTURE, not a content-value judgment')
    for item in result['items']:
        quote = item['context']
        item.update(quote=quote, without='', with_reading='STRUCTURAL FIXTURE with text',
                    without_reading='STRUCTURAL FIXTURE without text', effect='information',
                    reason='STRUCTURAL FIXTURE, no semantic quality claim', decision='keep')
    return result
