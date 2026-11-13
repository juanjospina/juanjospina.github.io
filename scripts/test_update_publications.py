"""Run: python3 scripts/test_update_publications.py"""
import update_publications as up
up.crossref = lambda title: {}  # keep the check offline

ROW = ('<tr class="gsc_a_tr"><td class="gsc_a_t"><a href="/citations?view_op=view_citation&amp;citation_for_view=X:abc-1_Z"'
       ' class="gsc_a_at">A &lt;b&gt;Paper&lt;/b&gt;</a><div class="gs_gray">J Ospina, DM Fobes, ...</div>'
       '<div class="gs_gray">IEEE Access 9, 1-2<span class="gs_oph">, 2021</span></div></td>'
       '<td class="gsc_a_c"><a href="" class="gsc_a_ac gs_ibl">42</a></td>'
       '<td class="gsc_a_y"><span class="gsc_a_h gsc_a_hc gs_ibl">2021</span></td></tr>')
STATS = "".join(f'<td class="gsc_rsb_std">{n}</td>' for n in (100, 50, 7, 6, 5, 4))

stats, rows = up.parse_scholar(STATS + ROW)
assert stats == {"citations": 100, "h_index": 7, "i10_index": 5}, stats
r = rows[0]
assert (r["id"], r["cites"], r["year"], r["venue"]) == ("abc-1_Z", 42, 2021, "IEEE Access 9, 1-2"), r

data = {"stats": {**stats, "updated": "2026-01-01"},
        "publications": {"a": {**up.new_entry({**r, "venue": ""}), "hide": False, "cites": 42, "url": "javascript:alert(1)"}}}
html = up.render(data)
assert "<b>Paper</b>" not in html and "&lt;b&gt;Paper" in html  # Scholar text is escaped
assert "javascript:" not in html                                # unsafe URLs dropped
assert "<strong>J. Ospina</strong>, D. M. Fobes et al." in html
assert up.pub_type("2019 IEEE PES General Meeting") == "Conference" and up.pub_type("IEEE Access 9") == "Journal"
print("ok")

# A Scholar entry matching a hand-added one is hidden, not duplicated
data = {"publications": {"manual": {"title": "A <b>Paper</b>", "year": 2021}}}
up.merge(data, stats, rows)
assert data["publications"]["abc-1_Z"]["hide"] is True
print("ok (dedupe)")
