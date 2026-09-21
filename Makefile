SHELL       := bash
.SHELLFLAGS := -eu -o pipefail -c

PACKWIZ ?= packwiz
PYTHON  ?= python3
TOOLS   ?= tools

METAS   = $(wildcard $(V)/mods/*.pw.toml $(V)/resourcepacks/*.pw.toml)
PACK    = $(shell grep -m1 '^version' $(V)/pack.toml 2>/dev/null | cut -d'"' -f2)
OUT     = $(CURDIR)/$(V)/build
MRPACK  = $(OUT)/$(V)-$(PACK).mrpack
CFZIP   = $(OUT)/$(V)-$(PACK).zip

.PHONY: build release version check-v check check-meta check-cf check-mr \
        add link adopt sync update clean push release-push

# --- guards ------------------------------------------------------------

check-v:
	@test -n "$(V)" || { echo "usage: make <target> V=<mc-version>"; exit 1; }
	@test -f "$(V)/pack.toml" || { echo "no pack.toml in $(V)/"; exit 1; }
	@test -n "$(PACK)" || { echo "no version in $(V)/pack.toml"; exit 1; }
	@test -n "$(METAS)" || { echo "no metafiles in $(V)/"; exit 1; }

# Every metafile needs both providers.
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

# Adds a mod not yet in the pack. CF is the project URL.
add: check-v
	@test -n "$(MR)" -a -n "$(CF)" || { echo "usage: make add V=<mc-version> MR=<modrinth-slug> CF=<curseforge-url>"; exit 1; }
	@test ! -f "$(V)/mods/$(MR).pw.toml" -a ! -f "$(V)/resourcepacks/$(MR).pw.toml" \
		|| { echo "$(MR) is already in the pack; use: make link V=$(V) CF=<url> TARGET=$(MR)"; exit 1; }
	cd $(V) && $(PACKWIZ) mr add "$(MR)"
	$(PYTHON) $(TOOLS)/curseforge.py $(V) link "$(CF)"
	cd $(V) && $(PACKWIZ) refresh
	@$(MAKE) --no-print-directory check-meta V=$(V)

# Copies project ids from another pack, matching metafile names.
# Run sync afterwards to fill in the file ids.
adopt: check-v
	@test -n "$(FROM)" || { echo "usage: make adopt V=<mc-version> FROM=<source-version>"; exit 1; }
	@test -f "$(FROM)/pack.toml" || { echo "no pack.toml in $(FROM)/"; exit 1; }
	$(PYTHON) $(TOOLS)/curseforge.py $(V) adopt "$(FROM)"
	cd $(V) && $(PACKWIZ) refresh

# Links a mod already in the pack, leaving its version alone.
link: check-v
	@test -n "$(CF)" || { echo "usage: make link V=<mc-version> CF=<curseforge-url> [TARGET=<metafile>]"; exit 1; }
	$(PYTHON) $(TOOLS)/curseforge.py $(V) link "$(CF)" $(if $(TARGET),--target "$(TARGET)")
	cd $(V) && $(PACKWIZ) refresh
	@$(MAKE) --no-print-directory check-meta V=$(V)

sync: check-v
	$(PYTHON) $(TOOLS)/curseforge.py $(V) sync
	cd $(V) && $(PACKWIZ) refresh
	@$(MAKE) --no-print-directory check-meta V=$(V)

update: check-v
	cd $(V) && $(PACKWIZ) update --all
	@$(MAKE) --no-print-directory sync V=$(V)

# --- build -------------------------------------------------------------

build: check-v check-meta
	@mkdir -p $(OUT)
	cd $(V) && $(PACKWIZ) refresh
	cd $(V) && $(PACKWIZ) mr export -o "$(MRPACK)"
	cd $(V) && $(PACKWIZ) cf export -o "$(CFZIP)"
	@$(MAKE) --no-print-directory check V=$(V)

check: check-cf check-mr

# No jars in overrides/: CurseForge rejects the upload.
check-cf: check-v
	@test -f "$(CFZIP)" || { echo "$(notdir $(CFZIP)) not found, run make build"; exit 1; }
	@bundled=$$(unzip -Z1 "$(CFZIP)" | grep -E '^overrides/(mods|resourcepacks)/' || true); \
	if [ -n "$$bundled" ]; then \
		echo "$(notdir $(CFZIP)): $$(echo "$$bundled" | wc -l) bundled files, upload would be rejected"; \
		echo "$$bundled" | sed 's/^/  /'; \
		exit 1; \
	fi
	@echo "$(notdir $(CFZIP)): no bundled files"

# One indexed download per metafile.
check-mr: check-v
	@test -f "$(MRPACK)" || { echo "$(notdir $(MRPACK)) not found, run make build"; exit 1; }
	@bundled=$$(unzip -Z1 "$(MRPACK)" | grep -E '^overrides/(mods|resourcepacks)/' || true); \
	if [ -n "$$bundled" ]; then \
		echo "$(notdir $(MRPACK)): $$(echo "$$bundled" | wc -l) bundled files"; \
		echo "$$bundled" | sed 's/^/  /'; \
		exit 1; \
	fi
	@expected=$$(ls $(METAS) | wc -l); \
	indexed=$$(unzip -p "$(MRPACK)" modrinth.index.json \
		| $(PYTHON) -c 'import json,sys; print(len(json.load(sys.stdin)["files"]))'); \
	echo "$(notdir $(MRPACK)): $$indexed/$$expected indexed downloads"; \
	test "$$indexed" -eq "$$expected"

clean: check-v
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
	git commit -m --allow-empty "build: $(V) release $(TAG)"
	git tag -a "$(V)-$(TAG)" -m "$(V) $(TAG)"
	@echo "artifacts in $(OUT)/"

push:
	git push --follow-tags

release-push: release push
