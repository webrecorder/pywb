from pywb.rewrite.templateview import JinjaEnv


def render_head_insert(attack):
    template = JinjaEnv().jinja_env.get_template('head_insert.html')

    return template.render(
        cdx={
            'url': 'https://example.test/' + attack,
            'timestamp': attack,
        },
        top_url=attack,
        wb_url={
            'timestamp': attack,
            'is_banner_only': False,
        },
        wb_prefix=attack,
        replay_mod=attack,
        is_framed=False,
        is_live=False,
        coll=attack,
        env={},
        static_prefix='/static',
        config={
            'enable_auto_fetch': False,
            'enable_flash_video_rewrite': False,
            'transclusions_version': 0,
        },
        wombat_ts=attack,
        wombat_sec=attack,
        inject_scripts=[],
        custom_banner_html='<div id="custom-banner"></div>',
    )


def test_head_insert_uses_html_safe_json():
    attack = '</script><script>globalThis.pwned = true</script>'

    rendered = render_head_insert(attack)

    assert attack not in rendered
    assert '\\u003c' in rendered
    assert 'wbinfo.proxy_magic = "";' in rendered
    assert rendered.count('<script>') == 2


def test_head_insert_preserves_custom_banner_html():
    rendered = render_head_insert('safe')

    assert '<div id="custom-banner"></div>' in rendered
