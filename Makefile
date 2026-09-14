SHELL       := bash
.SHELLFLAGS := -eu -o pipefail -c

PACKWIZ ?= packwiz
PYTHON  ?= python3
TOOLS   ?= tools
OUT     ?= $(CURDIR)/build

METAS = $(V)/mods/*.pw.toml $(V)/resourcepacks/*.pw.toml

.PHONY: build release version check-v check check-meta check-cf check-mr \
        detect update clean push release-push

# --- guards ------------------------------------------------------------

check-v:
	@test -n "$(V)" || { echo "usage: make <target> V=<mc-version>"; exit 1; }
	@test -f "$(V)/pack.toml" || { echo "no pack.toml in $(V)/"; exit 1; }

# Every metafile must carry both providers. [update.curseforge] produces a
# manifest entry in the CurseForge zip; without it the jar is bundled into
# overrides/ and the upload is rejected. [update.modrinth] keeps the direct
# CDN link in the .mrpack, since forgecdn is not on Modrinth's domain
# allowlist.
check-meta: check-v
	@no_cf=$$(grep -L '^\[update\.curseforge\]' $(METAS) || true); \
	no_mr=$$(grep -L '^\[update\.modrinth\]' $(METAS) || true); \
	if [ -n "$$no_cf" ]; then \
		echo "missing [update.curseforge]:"; \
		echo "$$no_cf" | sed 's/^/  /'; \
	fi; \
	if [ -n "$$no_mr" ]; then \
		echo "missing [update.modrinth]:"; \
		echo "$$no_mr" | sed 's/^/  /'; \
	fi; \
	test -z "$$no_cf$$no_mr" || exit 1
	@echo "metadata: $$(ls $(METAS) | wc -l) files, both providers present"

# --- metadata ----------------------------------------------------------

# `detect` resolves CurseForge ids but rewrites the download source and
# drops [update.modrinth]; restore-modrinth.py reapplies the committed
# Modrinth metadata and keeps only the resolved ids.
detect: check-v
	cd $(V) && $(PACKWIZ) curseforge detect
	$(PYTHON) $(TOOLS)/restore-modrinth.py $(V)
	cd $(V) && $(PACKWIZ) refresh
	@$(MAKE) --no-print-directory check-meta V=$(V)

# CurseForge file ids are version-specific, so they must be resolved again
# after every dependency bump.
update: check-v
	cd $(V) && $(PACKWIZ) update --all
	@$(MAKE) --no-print-directory detect V=$(V)

# --- build -------------------------------------------------------------

build: check-v check-meta
	@mkdir -p $(OUT)
	cd $(V) && $(PACKWIZ) refresh
	cd $(V) && $(PACKWIZ) mr export -o "$(OUT)/$(V).mrpack"
	cd $(V) && $(PACKWIZ) cf export -o "$(OUT)/$(V).zip"
	@$(MAKE) --no-print-directory check V=$(V)

check: check-cf check-mr

# Mirrors the CurseForge upload validator, which rejects archives shipping
# jars that belong to CurseForge-hosted projects.
check-cf:
	@test -f "$(OUT)/$(V).zip" || { echo "$(OUT)/$(V).zip not found, run make build"; exit 1; }
	@bundled=$$(unzip -Z1 "$(OUT)/$(V).zip" | grep -E '^overrides/(mods|resourcepacks)/' || true); \
	if [ -n "$$bundled" ]; then \
		echo "$(V).zip: $$(echo "$$bundled" | wc -l) bundled files, upload would be rejected"; \
		echo "$$bundled" | sed 's/^/  /'; \
		exit 1; \
	fi
	@echo "$(V).zip: no bundled files"

# The index must list one direct download per metafile; a shortfall means
# some mods fell back to overrides/.
check-mr:
	@test -f "$(OUT)/$(V).mrpack" || { echo "$(OUT)/$(V).mrpack not found, run make build"; exit 1; }
	@bundled=$$(unzip -Z1 "$(OUT)/$(V).mrpack" | grep -E '^overrides/(mods|resourcepacks)/' || true); \
	if [ -n "$$bundled" ]; then \
		echo "$(V).mrpack: $$(echo "$$bundled" | wc -l) bundled files"; \
		echo "$$bundled" | sed 's/^/  /'; \
		exit 1; \
	fi
	@expected=$$(ls $(METAS) | wc -l); \
	indexed=$$(unzip -p "$(OUT)/$(V).mrpack" modrinth.index.json \
		| $(PYTHON) -c 'import json,sys; print(len(json.load(sys.stdin)["files"]))'); \
	echo "$(V).mrpack: $$indexed/$$expected indexed downloads"; \
	test "$$indexed" -eq "$$expected"

clean:
	rm -rf $(OUT)

# --- release -----------------------------------------------------------

version: check-v
	@grep '^version' $(V)/pack.toml

release: check-v
	@test -n "$(TAG)" || { echo "usage: make release V=<mc-version> TAG=<x.y.z>"; exit 1; }
	@git diff --quiet && git diff --cached --quiet || { echo "working tree dirty, commit first"; exit 1; }
	sed -i 's/^version = .*/version = "$(TAG)"/' $(V)/pack.toml
	$(MAKE) build V=$(V)
	git add $(V)/pack.toml $(V)/index.toml $(V)/mods $(V)/resourcepacks
	git commit -m "build: $(V) release $(TAG)"
	git tag -a "$(V)-$(TAG)" -m "$(V) $(TAG)"
	@echo "artifacts in $(OUT)/"

push:
	git push --follow-tags

release-push: release push
