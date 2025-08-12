import warnings

from brownie import Contract, accounts, chain, ReUsdFromOracleVault, OracleProxy, AMM

warnings.filterwarnings("ignore")

# This script tests the deployment of the OracleProxy.vy contract with the implementation contract
# It deploys a test LlamaLend market with oracle_impl
# It checks that price() returns a good value and changes the oracle price to check price_w() updates properly in the AMM
# Note that there is a deviation check when setting a new oracle_impl, if it exceeds the value specified in the proxy, it will revert

# LlamaLend factory
factory = Contract('0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0')

def deploy():

	# Deploy oracle implementation using sfrxUSD vault as stand in
	oracle_impl = ReUsdFromOracleVault.deploy(
		'0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6', # sfrxUSD vault
		'0x07Ac1E016D4335FB833666ed5C43846162d2B7e8', # reUSD oracle contract
		{'from': accounts[0]}
	)


	# Deploy the Proxy contract, using the factory's address to get the admin
	proxy = OracleProxy.deploy(
		oracle_impl.address, # implementation
		factory.address, # factory
		500, # Max deviation in BPS
		{'from': accounts[0]}
	)

	# Deploy LlamaLend market using proxy as oracle
	market = factory.create(
		'0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E', # borrowed
		'0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6', # collateral, sfrxUSD as a stand in
		300, # A
		2000000000000000, # fee
		13000000000000000, # loan_discount
		10000000000000000, # liq_discount
		proxy, # oracle
		'sfrxUSD', # name
		31709791, # min_rate
		7927447995, # max_rate
		{'from': accounts[0]}
	)

	return market, proxy

def test_down_manipulation():

	# deploy all oracles and test market
	market, proxy = deploy()

	amm = AMM.at(market.events["NewVault"]["amm"])
	price_oracle_proxy = amm.price_oracle_contract()
	impl = OracleProxy.at(price_oracle_proxy).implementation()

	price = amm.price_oracle() /1e18

	print("_____IMPL1 INSTANTIATED_____")
	print(f"Market oracle proxy at address {price_oracle_proxy}")
	print(f"Proxy implementation at address {impl}")
	print(f"Oracle price in AMM is {price}")

	# manipulate reUSD down
	reusd = Contract('0x57aB1E0003F623289CD798B1824Be09a793e4Bec')
	reusd_whale = accounts.at('0x00000000efe883b3304aFf71eaCf72Dbc3e1b577', force=True)
	reusd_scrvusd = Contract('0xc522A6606BBA746d7960404F22a3DB936B6F4F50')
	reusd.approve(reusd_scrvusd, reusd.balanceOf(reusd_whale), {'from': reusd_whale})
	reusd_scrvusd.exchange(0, 1, reusd.balanceOf(reusd_whale), 0, reusd_whale, {'from': reusd_whale})
	chain.sleep(86400)

	amm.exchange(0,1,0,0,accounts[0], {'from': accounts[0]})
	price = amm.price_oracle() / 1e18

	print(f"_____Price_w TEST_____")
	print(f"After manipulating reUSD/scrvUSD price oracle and calling exchange in AMM (price_w call), price in AMM is {price}")
	print(f"Max deviation is {proxy.max_deviation()}")

	# test setting max deviation
	admin = accounts.at(factory.admin(), force=True)
	proxy.set_max_deviation(2000, {'from': admin})
	print(f"Max deviation is {proxy.max_deviation()}")


def test_up_manipulation():

	# deploy all oracles and test market
	market, proxy = deploy()

	amm = AMM.at(market.events["NewVault"]["amm"])
	price_oracle_proxy = amm.price_oracle_contract()
	impl = OracleProxy.at(price_oracle_proxy).implementation()

	price = amm.price_oracle() /1e18

	print("_____IMPL1 INSTANTIATED_____")
	print(f"Market oracle proxy at address {price_oracle_proxy}")
	print(f"Proxy implementation at address {impl}")
	print(f"Oracle price in AMM is {price}")

	admin = accounts.at(factory.admin(), force=True)

	# manipulate reUSD up
	scrvusd = Contract('0x0655977FEb2f289A4aB78af67BAB0d17aAb84367')
	crvusd = Contract('0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E')
	crvusd_whale = accounts.at('0xA920De414eA4Ab66b97dA1bFE9e6EcA7d4219635', force=True)

	crvusd.approve('0x0655977FEb2f289A4aB78af67BAB0d17aAb84367', crvusd.balanceOf(crvusd_whale), {'from': crvusd_whale})
	scrvusd.deposit(crvusd.balanceOf(crvusd_whale), crvusd_whale, {'from': crvusd_whale})

	reusd_scrvusd = Contract('0xc522A6606BBA746d7960404F22a3DB936B6F4F50')

	scrvusd.approve(reusd_scrvusd, scrvusd.balanceOf(crvusd_whale), {'from': crvusd_whale})
	reusd_scrvusd.exchange(1, 0, scrvusd.balanceOf(crvusd_whale), 0, crvusd_whale, {'from': crvusd_whale})

	chain.sleep(86400)

	amm.exchange(0,1,0,0,accounts[0], {'from': accounts[0]})
	price = amm.price_oracle() / 1e18

	print(f"_____Price_w TEST_____")
	print(f"After manipulating reUSD/scrvUSD price oracle and calling exchange in AMM (price_w call), price in AMM is {price}")
	print(f"Max deviation is {proxy.max_deviation()}")

	# test setting max deviation
	admin = accounts.at(factory.admin(), force=True)
	proxy.set_max_deviation(2000, {'from': admin})
	print(f"Max deviation is {proxy.max_deviation()}")