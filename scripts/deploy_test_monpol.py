from brownie import Contract, accounts, EMAMonetaryPolicy, chain, SfrxusdRateCalc

FRXUSD = "0xCAcd6fd266aF91b8AeD52aCCc382b4e165586E29"
SFRXUSD = "0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6"

frxusd = Contract(FRXUSD)
sfrxusd = Contract(SFRXUSD)

controller = Contract('0x3DE37c38739dFb83b7A902842bF5393040f7BF50')
vault = Contract('0x8E3009b59200668e1efda0a2F2Ac42b24baa2982')
admin = accounts.at('0x40907540d8a6C65c637785e8f8B742ae6b0b9968', force=True)

def sfrxusd_apr():
    cycle_end: uint256 = 0
    last_sync: uint256 = 0
    reward_amt: uint256 = 0
    cycle_end, last_sync, reward_amt = sfrxusd.rewardsCycleData()
    print(f"{cycle_end}, {last_sync}, {reward_amt}")
    print(f"duration: {cycle_end - last_sync}")
    if cycle_end <= last_sync:
        return 0

    assets: uint256 = sfrxusd.storedTotalAssets()
    print(f"Assets: {assets}")
    if assets == 0:
        assets = 1

    max_distro: uint256 = sfrxusd.maxDistributionPerSecondPerAsset()
    print(f"Max Distro: {max_distro}")
    duration: uint256 = cycle_end - last_sync
    frax_per_second: uint256 = reward_amt / duration
    frax_per_second = frax_per_second * 10**18 / assets
    print(f"Frax per second: {frax_per_second}")
    rate = min(frax_per_second, max_distro)
    apr = rate * 365 * 86400 / 1e16
    print(f"frxUSD apr is {apr}%")

def deploy():

	# Deploy Contracts
	calculator = SfrxusdRateCalc.deploy('0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6', {'from': accounts[0]})

	monpol = EMAMonetaryPolicy.deploy(
		"0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0", # FACTORY
		calculator.address, # RATE_CALCULATOR
		"0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E", # BORROWED_TOKEN
		850000000000000000, # TARGET_U
		200000000000000000, # LOW_RATIO
		7200000000000000000, # HIGH_RATIO
		0, # RATE_SHIFT
		{'from': accounts[0], 'priority_fee': "0.04 gwei"}
	)


	# Initial values read
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate in LlamaLend vault with old contract is {rate:.2f}%")

	controller.set_monetary_policy(monpol, {'from': admin})
	controller.save_rate({'from': accounts[0]})

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate in LlamaLend vault with new SecondaryMonPol contract is {rate:.2f}%")

	# set sfrxUSD apr to 4%
	sfrxusd.setMaxDistributionPerSecondPerAsset(1278821663, {'from': accounts.at('0xB1748C79709f4Ba2Dd82834B8c82D4a505003f27', force=True)})
	sfrxusd.syncRewardsAndDistribution({'from': accounts[0]})

	sfrxusd_apr()

	chain.sleep(86400*10)
	controller.save_rate({'from': accounts[0]})

	print(f"Rate in calculator is {calculator.rate()}")
	print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')


	#set sfrxUSD rate to 8%

	sfrxusd.setMaxDistributionPerSecondPerAsset(2557643327, {'from': accounts.at('0xB1748C79709f4Ba2Dd82834B8c82D4a505003f27', force=True)})
	sfrxusd.syncRewardsAndDistribution({'from': accounts[0]})

	sfrxusd_apr()

	print("AFTER MESS WITH RATES")
	print(f"Rate in calculator is {calculator.rate()}")
	
	counter = 0
	while counter < 24:
		controller.save_rate({'from': accounts[0]})
		monpol_rate = monpol.ma_rate()*86400*365/1e16
		fraction = monpol_rate / 8.0657839960272 * 100
		print(f'MonPol ma_rate() is {monpol_rate:.2f}%, {fraction:.2f}% of target {counter} hours after apr rise.')
		rate = vault.borrow_apr() / 1e16
		# print(f"sfrxUSD-long rate in LlamaLend vault {counter} days after apr rise is {rate:.2f}%")
		chain.sleep(7200)
		counter += 1

	# Increase market utilization
	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print("INCREASE MARKET UTILIZATION TEST")
	print(f"market utilization initially is {borrowed/supplied*100:2f}%")

	borrower = accounts.at('0x70644a67a01971c28395327Ca9846E0247313bC9', force=True)
	borrower_bal = frxusd.balanceOf(borrower)

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate before increasing market utilization is {rate:.2f}%")
	print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')

	sfrxusd.approve(controller, 10000000e18, {'from': borrower})
	
	controller.create_loan(2100000e18, 2000000e18, 4, {'from': borrower})

	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print(f"market utilization after create loan is {borrowed/supplied*100:2f}%")

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate after increasing market utilization is {rate:.2f}%")

	
	# Decrease sfrxUSD APR
	print("TEST REDUCING SFRXUSD APR TO NEAR 0")
	sfrxusd.setMaxDistributionPerSecondPerAsset(1, {'from': accounts.at('0xB1748C79709f4Ba2Dd82834B8c82D4a505003f27', force=True)})
	sfrxusd.syncRewardsAndDistribution({'from': accounts[0]})
	sfrxusd_apr()

	counter = 0
	while counter < 24:
		controller.save_rate({'from': accounts[0]})
		print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')
		rate = vault.borrow_apr() / 1e16
		print(f"sfrxUSD-long rate in LlamaLend vault {counter} hours after apr decrease is {rate:.2f}%")
		chain.sleep(7200)
		counter += 1

