"""Where each client lives, and what shape its Gateway-facing code takes.

Two repositories speak Gateway's HTTP API by hand: hummingbot's GatewayHttpClient and
hummingbot-api's GatewayClient. Both were written against an API defined in a third
repository, so every route rename and field rename over there is invisible here until a
call 404s or a `.get()` quietly reads None. This table is what lets one checker read both
without either repo carrying a copy of the other's spec.

Add a repo by adding an entry. Everything below is read out of source with `ast` and
regexes -- nothing is imported -- so no conda environment is needed to run the checks.
"""
import os
from pathlib import Path

# Interpolated path segments stand for a value chosen at runtime. Each is expanded to the
# values it can take so the route check stays exact instead of pattern-matching.
SEGMENT_VALUES = {
    "{trading_type}": ["router", "clmm", "amm"],
}

# Real Gateway routes that carry no TypeBox schema, so @fastify/swagger omits them from
# the spec. Named with where they live, so the exemption stays reviewable and a genuinely
# deleted route cannot hide behind it.
UNSCHEMAD_ROUTES = {
    "/restart",  # src/app.ts -- server.post('/restart'), no schema attached
}


def _default(env_var: str, name: str) -> Path:
    return Path(os.environ.get(env_var, Path.home() / name)).expanduser()


REPOS = {
    "hummingbot": {
        "root": _default("HUMMINGBOT_DIR", "hummingbot"),
        # The module that builds the requests.
        "client": "hummingbot/core/gateway/gateway_http_client.py",
        # Path literals passed to api_request(), plain or f-string.
        "path_regex": r'api_request\(\s*\n?\s*"[a-z]+"\s*,\s*\n?\s*f?"([^"]+)"',
        # The LP routes never appear as a literal: _lp_route(trading_type, verb) assembles
        # them and hands the result to api_request as a variable. Reading the verbs
        # separately is what makes the check cover them -- while it did not, three sat on
        # Gateway's pre-rename names (quote-position, add-liquidity, remove-liquidity) and
        # the check reported everything fine.
        "lp_routes": True,
        # Every module that speaks Gateway's wire format: the client that builds the
        # requests, and the connector layer that reads the responses back apart.
        "wire_sources": [
            "hummingbot/core/gateway/gateway_http_client.py",
            "hummingbot/connector/gateway/gateway.py",
            "hummingbot/connector/gateway/gateway_base.py",
        ],
        # camelCase keys that address Gateway's YAML config tree rather than an HTTP
        # field. /config returns the config as-is, so these arrive as namespaced names
        # ("solana.defaultWallet") that no route schema declares. Listed individually so a
        # renamed wire field cannot hide behind the exemption.
        "config_tree_keys": {"defaultNetwork", "defaultWallet", "nativeCurrencySymbol"},
        # camelCase strings that are this repo's own values, not Gateway field names. The
        # regex cannot tell a dict key from any other string literal.
        "local_constants": {"txDataUnavailable"},
        "generated": "hummingbot/core/gateway/gateway_models.py",
        # setup.py's python_requires floor, not whatever interpreter is to hand: 3.12
        # emits StrEnum, which 3.10 does not have, so the file would differ by target.
        "target_python": "3.10",
        # Hand-written transcriptions of Gateway response schemas, paired with the
        # generated model of the schema each is built from. Each is filled by handing
        # Gateway's response straight to pydantic, so a field Gateway stops sending stops
        # arriving -- silently, as a default.
        "mirrors": {
            "file": "hummingbot/connector/gateway/gateway.py",
            # Gateway's token entries are anonymous inside TokensResponse, so the
            # generator names that item type `Token`.
            "pairs": [
                ("TokenInfo", "Token"),
                ("AMMPoolInfo", "AmmPoolInfo"),
                ("CLMMPoolInfo", "ClmmPoolInfo"),
                ("AMMPositionDetail", "PositionDetail"),
                ("AMMPositionInfo", "AmmPositionInfo"),
                ("CLMMPositionInfo", "ClmmPositionInfo"),
            ],
            # Fields the position models add for this side's own use. They are filled in
            # after construction from token metadata, so Gateway never sends them and
            # their absence from its schema is correct rather than drift.
            "locally_populated": {"base_token", "quote_token"},
        },
    },
    "hummingbot-api": {
        "root": _default("HUMMINGBOT_API_DIR", "hummingbot-api"),
        "client": "services/gateway_client.py",
        # Both plain and f-strings, since the trading routes interpolate the type.
        "path_regex": r'_request\(\s*"[A-Z]+"\s*,\s*f?"([^"]+)"',
        "lp_routes": False,
        "wire_sources": ["services/gateway_client.py"],
        "config_tree_keys": {"apiKeys", "defaultNetwork", "defaultWallet"},
        "local_constants": set(),
        "generated": "models/gateway_generated.py",
        "target_python": "3.12",
        "mirrors": {
            "file": "models/gateway_trading.py",
            # A model appears once per schema it is fed from: the create-pool and
            # write-transaction responses are shared across the AMM and CLMM surfaces, and
            # each of those schemas must independently satisfy it.
            "pairs": [
                ("CLMMPoolInfoResponse", "ClmmPoolInfo"),
                ("CLMMPoolBin", "BinLiquidity"),
                ("CLMMQuotePositionResponse", "ClmmQuoteLiquidityResponse"),
                ("AMMPoolInfoResponse", "AmmPoolInfo"),
                ("AMMPositionInfoResponse", "AmmPositionInfo"),
                ("AMMPositionDetail", "PositionDetail"),
                ("AMMQuoteLiquidityResponse", "AmmQuoteLiquidityResponse"),
                ("AMMCreatePoolResponse", "AmmCreatePoolResponse"),
                ("AMMCreatePoolResponse", "ClmmCreatePoolResponse"),
                # Gateway dropped /trading/amm/{open,close}: open was a synonym for add
                # without a position address, and close is what remove does at 100%, which
                # is why the remove response carries positionRentRefunded.
                ("AMMTransactionResponse", "AmmAddLiquidityResponse"),
                ("AMMTransactionResponse", "AmmRemoveLiquidityResponse"),
            ],
            "locally_populated": set(),
        },
    },
}
