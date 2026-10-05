from vireo.analytics.peer_groups import build_peer_groups

def roster(agent, tier, team, site="Pune", shift="Day", start="2025-01-01", end=""):
    return {"agent_id":agent,"tier":tier,"team":team,"site":site,"shift":shift,"from_date":start,"to_date":end}

def test_tier_two_never_mixes_with_tier_one():
    rows=[roster(f"a{i}","1","Frontline") for i in range(3)]+[roster(f"b{i}","2","Escalations & Warranty") for i in range(3)]
    groups=build_peer_groups(rows)
    assert len({r["comparison_group"] for r in groups[:3]})==1
    assert len({r["comparison_group"] for r in groups[3:]})==1
    assert groups[0]["comparison_group"]!=groups[3]["comparison_group"]

def test_assignment_changes_remain_distinct():
    rows=[roster("a1","1","Chat","Pune","Day","2025-01-01","2025-06-30"),roster("a1","1","Email","Delhi","Night","2025-07-01"),
          roster("a2","1","Chat","Pune","Day"),roster("a3","1","Chat","Pune","Day"),roster("a4","1","Email","Delhi","Night")]
    groups=build_peer_groups(rows)
    a1=[r for r in groups if r["agent_id"]=="a1"]
    assert len(a1)==2
    assert a1[0]["comparison_group"]!=a1[1]["comparison_group"]

def test_small_team_falls_back_to_same_tier_and_too_small_tier_is_unsupported():
    rows=[roster("a1","1","Tiny A"),roster("a2","1","Tiny B"),roster("a3","1","Tiny C"),roster("b1","2","Small"),roster("b2","2","Small")]
    groups=build_peer_groups(rows)
    assert all(r["peer_fallback_level"]=="tier_only" for r in groups[:3])
    assert all(not r["peer_supported"] for r in groups[3:])
