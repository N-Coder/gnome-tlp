#!/bin/python3

import sh

for name, objs in (
        ("ac-eco-fix.svg", ("fixed", "eco", "ac-eco")),
        ("ac-pow-aut.svg", ("power", "ac-power")),
        ("ac-pow-fix.svg", ("fixed", "power", "ac-power")),
        ("bat-eco-aut.svg", ("eco", "bat-eco")),
        ("bat-eco-fix.svg", ("fixed", "eco", "bat-eco")),
        ("bat-pow-fix.svg", ("fixed", "power", "bat-power")),
):
    sh.inkscape(
        "template.svg", actions=
        "select-all;%s;"
        "delete;"
        "export-overwrite;export-area-page;export-type:svg;export-plain-svg;"
        "export-filename:%s;"
        "export-do" % (";".join("unselect-by-id:" + s for s in objs), name)
    )
