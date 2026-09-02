.PHONY: build release version check-v

check-v:
	@test -n "$(V)" || { echo "usage: make <target> V=<mc-version>"; exit 1; }
	@test -f "$(V)/pack.toml" || { echo "no pack.toml in $(V)/"; exit 1; }

build: check-v
	cd $(V) && packwiz refresh && packwiz mr export && packwiz cf export --side client

version: check-v
	@grep '^version' $(V)/pack.toml

release: check-v
	@test -n "$(TAG)" || { echo "usage: make release V=<mc-version> TAG=<x.y.z>"; exit 1; }
	@git diff --quiet || { echo "working tree dirty, commit first"; exit 1; }
	sed -i 's/^version = .*/version = "$(TAG)"/' $(V)/pack.toml
	cd $(V) && packwiz refresh && packwiz mr export && packwiz cf export --side client
	git add $(V)/pack.toml $(V)/index.toml
	git commit -m "build: $(V) release $(TAG)"
	git tag -a "$(V)-$(TAG)" -m "$(V) $(TAG)"
	@echo "Done."

push:
	git push --follow-tags

release-push: release push
