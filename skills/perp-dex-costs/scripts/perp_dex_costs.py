#!/usr/bin/env python3
"""perp_dex_costs.py: pre-trade cost check for perp DEXs (Dinero en la Mesa API).

Standard library only.
Free:  best, costs, funding, delta, depth, venues, airdrops, changes, signup
Paid (USDC on Base via x402): scanner, points, route, plan, alerts
  python perp_dex_costs.py best --pair BTC --size 25000
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get('DLM_API', 'https://dineroenlamesa.com/agents/api').rstrip('/')
MARCA = 'hummingbot'          # lets the API count calls coming from this skill
MCP = 'https://dineroenlamesa.com/agents/mcp'

# Venues that have a Hummingbot connector (perpetuals)
CONECTORES = {'hyperliquid': 'hyperliquid_perpetual', 'dydx': 'dydx_v4_perpetual'}

COMO_PAGAR = ('How to pay: this tool is paid per call in USDC on Base via x402 (no account, no key). '
              'Use an x402-capable client (for example an agent with a Base / Coinbase wallet) on the same URL, '
              'or connect the MCP server ' + MCP + ' from an agent that can pay x402. '
              'You are only charged when the result is delivered.')


def pedir(herramienta, pago=False, **args):
    q = {k: v for k, v in args.items() if v is not None}
    q['c'] = MARCA
    url = '%s/%s?%s' % (API, herramienta, urllib.parse.urlencode(q))
    req = urllib.request.Request(url, headers={'User-Agent': 'hummingbot-skill-perp-dex-costs/1.1'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode('utf-8', 'replace')
        try:
            j = json.loads(cuerpo)
        except ValueError:
            j = {'error': cuerpo}
        if e.code == 402:
            # Paid tool: the server says what the call would deliver right now and its price
            print(str(j.get('error', 'Payment required.')).strip())
            print('\nURL: ' + url)
            print(COMO_PAGAR)
            sys.exit(0)
        sys.exit('API error %s: %s' % (e.code, str(j.get('error', cuerpo))[:300]))
    except urllib.error.URLError as e:
        sys.exit('Cannot reach %s: %s' % (API, e.reason))


def conector(vid):
    return CONECTORES.get(vid, '-')


def usd(x):
    return '-' if x is None else '%.2f' % x


def tabla(filas, cab):
    anchos = [max([len(str(c))] + [len(str(f[i])) for f in filas]) for i, c in enumerate(cab)]

    def lin(f):
        return '  '.join(str(v).ljust(anchos[i]) for i, v in enumerate(f)).rstrip()
    print(lin(cab))
    print('  '.join('-' * a for a in anchos))
    for f in filas:
        print(lin(f))


def altas(filas):
    """Account-opening links, with what the user gets by opening the account that way."""
    vistos = set()
    for v in filas:
        if v.get('signup_url') and v.get('id') not in vistos:
            vistos.add(v.get('id'))
            extra = ' (%s)' % v['signup_benefit'] if v.get('signup_benefit') else ''
            print('  %s: %s%s' % (v.get('name'), v['signup_url'], extra))


def fila_coste(v):
    return [v.get('rank', ''), v.get('name', v.get('id')), conector(v.get('id')), usd(v.get('round_trip_cost_usd')),
            v.get('round_trip_cost_bps', '-'), usd(v.get('fees_usd')), usd(v.get('slippage_usd')),
            (v.get('book') or {}).get('as_of', '-')]


CAB_COSTE = ['#', 'venue', 'hummingbot connector', 'cost $', 'bps', 'fees $', 'slippage $', 'book read at (UTC)']


def cmd_best(a):
    r = pedir('best_venue', pair=a.pair, size_usd=a.size, monthly_volume_usd=a.volume)
    if a.json:
        return print(json.dumps(r, indent=2))
    filas = [r.get('best') or {}] + list(r.get('runners_up') or [])
    print('Round trip (open + close at market) of %s $ of %s' % (r.get('size_usd'), r.get('pair')))
    tabla([fila_coste(v) for v in filas], CAB_COSTE)
    print('\nOpen an account:')
    altas(filas)


def cmd_costs(a):
    r = pedir('trading_cost', pair=a.pair, size_usd=a.size, monthly_volume_usd=a.volume)
    if a.json:
        return print(json.dumps(r, indent=2))
    filas = (r.get('venues') or [])[:a.limit]
    print('Round trip (open + close at market) of %s $ of %s, cheapest first' % (r.get('size_usd'), r.get('pair')))
    tabla([fila_coste(v) for v in filas], CAB_COSTE)
    sin = r.get('no_figure') or []
    if sin:
        print('\nNo figure: ' + '; '.join('%s (%s)' % (x.get('name'), x.get('reason')) for x in sin))
    print('\nOpen an account:')
    altas(filas)


def cmd_funding(a):
    r = pedir('funding_rates', pair=a.pair)
    if a.json:
        return print(json.dumps(r, indent=2))
    vs = sorted(r.get('venues') or [], key=lambda v: v.get('rate_8h') if v.get('rate_8h') is not None else 0)[:a.limit]
    print('Funding for %s, normalised to 8 h (positive: longs pay shorts)' % r.get('pair'))
    tabla([[v.get('name'), conector(v.get('id')), '%.5f%%' % (100 * v['rate_8h']) if v.get('rate_8h') is not None else '-',
            '%.2f%%' % v['apr_pct'] if v.get('apr_pct') is not None else '-',
            'longs' if v.get('longs_pay') else 'shorts', v.get('as_of', '-')] for v in vs],
          ['venue', 'hummingbot connector', 'rate / 8h', 'APR', 'who pays', 'read at (UTC)'])
    print('\nOpen an account:')
    altas(vs)


def cmd_delta(a):
    r = pedir('delta_neutral', pair=a.pair, size_usd_per_leg=a.size, days=a.days)
    if a.json:
        return print(json.dumps(r, indent=2))
    b = r.get('best') or {}
    if not b:
        return print('No pair nets a positive amount right now for %s.' % r.get('pair'))
    print('Best delta-neutral couple for %s, %s $ per leg, %s days (read %s)' % (r.get('pair'), r.get('size_usd_per_leg'), r.get('days'), r.get('as_of')))
    print('  long  %s (%s)' % (b.get('long_name'), conector(b.get('long'))))
    print('  short %s (%s)' % (b.get('short_name'), conector(b.get('short'))))
    print('  funding earned %s $ - entry and exit %s $ = net %s $' % (usd(b.get('funding_earned_usd')), usd(b.get('entry_exit_cost_usd')), usd(b.get('net_usd'))))
    print('Open an account:')
    for lado in ('long', 'short'):
        if b.get('signup_' + lado):
            extra = ' (%s)' % b['signup_%s_benefit' % lado] if b.get('signup_%s_benefit' % lado) else ''
            print('  %s: %s%s' % (b.get(lado + '_name'), b['signup_' + lado], extra))
    print('Rates change every hour: a snapshot, not a forecast. Every pair and venue couple, every minute: `scanner` (paid).')


def cmd_depth(a):
    r = pedir('depth', pair=a.pair)
    if a.json:
        return print(json.dumps(r, indent=2))
    vs = (r.get('venues') or [])[:a.limit]
    print('Order book depth for %s, tightest spread first (USD resting near mid)' % r.get('pair'))
    tabla([[v.get('name'), conector(v.get('id')), v.get('spread_bps', '-'),
            '%.0f / %.0f' % ((v.get('depth_usd_within_0_5pct') or {}).get('bids', 0), (v.get('depth_usd_within_0_5pct') or {}).get('asks', 0)),
            '%.0f / %.0f' % ((v.get('depth_usd_within_1pct') or {}).get('bids', 0), (v.get('depth_usd_within_1pct') or {}).get('asks', 0)),
            (v.get('book') or {}).get('as_of', '-')] for v in vs],
          ['venue', 'hummingbot connector', 'spread bps', 'bids/asks ±0.5% $', 'bids/asks ±1% $', 'read at (UTC)'])


def cmd_venues(a):
    r = pedir('list_venues')
    if a.json:
        return print(json.dumps(r, indent=2))
    vs = r.get('venues') or []
    print('%s perp DEXs covered (entry-tier fees verified in each venue\'s docs)' % len(vs))
    tabla([[v.get('id'), v.get('name'), conector(v.get('id')), v.get('order_book', '-'),
            '%.4f%%' % (100 * v['taker_fee_entry_tier']) if v.get('taker_fee_entry_tier') is not None else '-',
            '%.4f%%' % (100 * v['maker_fee_entry_tier']) if v.get('maker_fee_entry_tier') is not None else '-',
            v.get('fees_checked_on', '-')] for v in vs],
          ['id', 'venue', 'hummingbot connector', 'book', 'taker', 'maker', 'fees checked'])


def cmd_airdrops(a):
    r = pedir('live_airdrops')
    if a.json:
        return print(json.dumps(r, indent=2))
    xs = (r.get('airdrops') or [])[:a.limit]
    print('Open airdrop and points campaigns, next hard date first')
    tabla([[x.get('name'), x.get('stage', '-'),
            '; '.join('%s (%s days): %s' % (d.get('date'), d.get('days_left'), d.get('what')) for d in (x.get('next_dates') or [])) or '-']
           for x in xs], ['campaign', 'stage', 'next date'])
    print('\nJoin:')
    altas(xs)


def cmd_changes(a):
    r = pedir('changes', days=a.days)
    if a.json:
        return print(json.dumps(r, indent=2))
    for c in (r.get('changes') or [])[:a.limit]:
        print('%s  %s: %s -> %s' % (c.get('date'), c.get('name'), c.get('before'), c.get('now')))


def cmd_signup(a):
    r = pedir('signup_link', venue=a.venue)
    if a.json:
        return print(json.dumps(r, indent=2))
    extra = ' (%s)' % r['signup_benefit'] if r.get('signup_benefit') else ''
    print('%s: %s%s' % (r.get('name'), r.get('signup_url'), extra))


# ── paid tools (x402): without payment the server answers 402 with what the call would give right now ──
def cmd_scanner(a):
    r = pedir('delta_neutral_scanner', pago=True, size_usd_per_leg=a.size, days=a.days)
    print(json.dumps(r, indent=2))


def cmd_points(a):
    r = pedir('cost_per_point', pago=True)
    print(json.dumps(r, indent=2))


def cmd_route(a):
    r = pedir('farming_route', pago=True, weekly_budget_usd=a.budget, trade_size_usd=a.size)
    print(json.dumps(r, indent=2))


def cmd_plan(a):
    r = pedir('execution_plan', pago=True, pair=a.pair, size_usd=a.size, side=a.side, monthly_volume_usd=a.volume)
    print(json.dumps(r, indent=2))


def cmd_alerts(a):
    print('alerts (paid, 29 USDC per 30 days, up to 3 pairs): a signed webhook the minute a delta-neutral funding gap '
          'or a venue\'s trading cost crosses your threshold, checked every minute on the live books.')
    print('It needs a webhook URL and rules, so subscribe from an agent connected to the MCP server ' + MCP +
          ' (tool `alerts`). Your webhook is tested first: if it does not answer, you are not charged.')


COMANDOS = {
    'best': (cmd_best, 'cheapest venue for your size (free)'),
    'costs': (cmd_costs, 'every venue ranked by round-trip cost (free)'),
    'funding': (cmd_funding, 'funding per venue, normalised to 8 h (free)'),
    'delta': (cmd_delta, 'best delta-neutral couple for one pair, net of costs (free)'),
    'depth': (cmd_depth, 'spread and depth of every order book (free)'),
    'venues': (cmd_venues, 'perp DEXs covered and their entry-tier fees (free)'),
    'airdrops': (cmd_airdrops, 'open airdrop and points campaigns (free)'),
    'changes': (cmd_changes, 'what changed in tracked campaigns (free)'),
    'signup': (cmd_signup, 'account-opening link for a venue (free)'),
    'scanner': (cmd_scanner, 'every pair and venue couple every minute (paid, 0.10 USDC)'),
    'points': (cmd_points, 'airdrop points per dollar of fees this week (paid, 0.05 USDC)'),
    'route': (cmd_route, 'what your weekly farming budget buys on each venue (paid, 0.50 USDC)'),
    'plan': (cmd_plan, 'split a large order across venues (paid, 1 USDC, only if it saves 20 $+)'),
    'alerts': (cmd_alerts, 'webhook alerts on funding gaps or costs (paid, 29 USDC / 30 days)'),
}


def tamano(x):
    f = float(x)
    return int(f) if f.is_integer() else f


def main(argv=None):
    p = argparse.ArgumentParser(description='Pre-trade cost check for perp DEXs (Dinero en la Mesa).')
    sub = p.add_subparsers(dest='cmd', required=True)
    for nombre, (f, ayuda) in COMANDOS.items():
        s = sub.add_parser(nombre, help=ayuda)
        s.add_argument('--pair', default='BTC', type=str.upper)
        s.add_argument('--size', type=tamano, default=10000)
        s.add_argument('--volume', type=tamano, default=None)
        s.add_argument('--days', type=int, default=None)
        s.add_argument('--limit', type=int, default=10)
        s.add_argument('--venue', default='hyperliquid')
        s.add_argument('--budget', type=tamano, default=500)
        s.add_argument('--side', choices=['buy', 'sell'], default='buy')
        s.add_argument('--json', action='store_true')
        s.set_defaults(f=f)
    a = p.parse_args(argv)
    if a.cmd in ('delta', 'scanner') and a.days is None:
        a.days = 7
    a.f(a)


if __name__ == '__main__':
    main()
