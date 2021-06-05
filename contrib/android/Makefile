PYTHON = python3

# needs kivy installed or in PYTHONPATH

.PHONY: theming prepare prepare-testnet apk apk-testnet release release-testnet clean

theming:
	$(PYTHON) -m kivy.atlas ../../electrum_zcash/gui/kivy/theming/light 1024 ../../electrum_zcash/gui/kivy/theming/light/*.png
prepare:
	# running pre build setup
	@cp buildozer.spec ../../buildozer.spec
	# copy electrum-zcash to main.py
	@cp ../../electrum-zcash ../../main.py
prepare-testnet:
	@-cd ../..; sed -r "s:^(title =.*):\1 Testnet:" -i buildozer.spec
	@-cd ../..; sed -r "s:^(package.nam.*):\1_Testnet:" -i buildozer.spec
	@-cd ../..; sed -r "s:^(presp.*).png:\1_testnet.png:" -i buildozer.spec
	@-cd ../..; sed -r "s:^(icon.filename.*).png:\1_testnet.png:" -i buildozer.spec
	@-cd ../..; sed -r "s:^(icon.adaptive_foreground.*).png:\1_testnet.png:" -i buildozer.spec
apk:
	@make prepare
	@-cd ../..; buildozer android debug
	@make clean
apk-testnet:
	@make prepare
	@make prepare-testnet
	@-cd ../..; buildozer android debug
	@make clean
release:
	@make prepare
	@-cd ../..; buildozer android release
	@make clean
release-testnet:
	@make prepare
	@make prepare-testnet
	@-cd ../..; buildozer android release
	@make clean
clean:
	# Cleaning up
	# rename main.py to electrum
	@-rm ../../main.py
	# remove buildozer.spec
	@-rm ../../buildozer.spec
