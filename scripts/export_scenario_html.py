"""Generate a local self-contained review page; publication is a separate action."""
import argparse
from pathlib import Path

from application.planning import run_plan
from presentation.scenario_html import render_report, render_reports
from scripts.plan_synthetic import demo_request

CASES=(('Fri direktväg','baseline',False),('Syntetiskt hinder','baseline',True),
       ('Konstaterat vågöverskridande','weather-limit',False),
       ('Otillräckligt konservativt bevis','unverified',False),
       ('Markerad vågdatalucka','missing-waves',False))


def build_demo():
    return render_reports((title,run_plan(demo_request(scenario=scenario,blocked_direct=blocked)))
                          for title,scenario,blocked in CASES)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='Explicit målfil för genererad HTML')
    parser.add_argument('--report',type=Path,help='Visa en befintlig JSON-rapport istället för demosviten')
    args=parser.parse_args()
    try:
        page=render_report(args.report.read_text(),args.report.name) if args.report else build_demo()
        args.output.write_text(page,encoding='utf-8')
        print('HTML-visning genererad: '+str(args.output))
    except (ValueError,OSError) as error:
        parser.exit(2,str(error)+'\n')


if __name__=='__main__':
    main()
