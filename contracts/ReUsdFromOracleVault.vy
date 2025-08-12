# @version 0.3.10
"""
@title SreUsdFromOracleVault
@notice Price oracle that uses the reUSD oracle contract and applies a throttled
        vault pricePerShare (PPS) to produce USD per 1 vault share.
"""

interface Vault:
    def pricePerShare() -> uint256: view
    def convertToAssets(shares: uint256) -> uint256: view

interface CollateralOracle:
    def price() -> uint256: view  # reUSD/USD using agg price of crvUSD


VAULT: public(immutable(Vault))
ORACLE: public(immutable(CollateralOracle))

PPS_MAX_SPEED: constant(uint256) = 10**16 / 60  # Max speed of pricePerShare change

cached_price_per_share: public(uint256)
cached_timestamp: public(uint256)


@external
def __init__(vault: Vault, oracle: CollateralOracle):
    """
    @param vault   ERC4626 vault exposing pricePerShare()
    @param oracle  Collateral oracle returning USD price (1e18)
    """
    VAULT = vault
    ORACLE = oracle

    self.cached_price_per_share = VAULT.pricePerShare()
    self.cached_timestamp = block.timestamp


@internal
@view
def _pps() -> uint256:
    return min(VAULT.pricePerShare(), self.cached_price_per_share * (10**18 + PPS_MAX_SPEED * (block.timestamp - self.cached_timestamp)) / 10**18)


@internal
def _pps_w() -> uint256:
    pps: uint256 = min(VAULT.pricePerShare(), self.cached_price_per_share * (10**18 + PPS_MAX_SPEED * (block.timestamp - self.cached_timestamp)) / 10**18)
    self.cached_price_per_share = pps
    self.cached_timestamp = block.timestamp
    return pps


@internal
@view
def _raw_price(pps: uint256) -> uint256:
    p_collateral: uint256 = ORACLE.price()
    return p_collateral * pps / 10**18


@external
@view
def price() -> uint256:
    return self._raw_price(self._pps())


@external
def price_w() -> uint256:
    return self._raw_price(self._pps_w())