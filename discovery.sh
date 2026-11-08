#!/usr/bin/env bash

# another *righteous entropy synthesis* by ⎰𝙉𝙄𝙈⎰ ...
# ----------------------------------------------------------------------------
#   NIM Substation One | Planet Earth | https://github.com/metasyndicate
# ----------------------------------------------------------------------------
#  [NIM.METASHELL.SUBSYSTEM]: ***discovery***
#    preliminary discovery for data design: a stated idea or work request ->
#    keywords -> ontology/schema search -> ontology selection -> merged,
#    standards-grounded baseline model, written as a referential bundle in
#    <project>/.nim/discovery/. Engine: lib/discovery (python3, stdlib only).
# ----------------------------------------------------------------------------

nim.source core fn log output validate

# === GLOBALS ===

[[ -z ${NIM_DISCOVERY_HOME} ]] && declare -gx NIM_DISCOVERY_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -z ${NIM_DISCOVERY_OUT} ]]  && declare -gx NIM_DISCOVERY_OUT=".nim/discovery"
[[ -z ${NIM_DISCOVERY_PY} ]]   && declare -gx NIM_DISCOVERY_PY="${PYTHON:-python3}"

# === PRIVATE ===

##! @function .nim.discovery.py.fn
##! @description run the python engine with the subsystem's lib on PYTHONPATH
##! @param [args...]       passed through to `python3 -m discovery`
##! @return the engine's exit status
function .nim.discovery.py.fn() {
    command -v "${NIM_DISCOVERY_PY}" >/dev/null 2>&1 || {
        nim.log.error "discovery: ${NIM_DISCOVERY_PY} not found in PATH"
        return 1; }
    PYTHONPATH="${NIM_DISCOVERY_HOME}/lib${PYTHONPATH:+:${PYTHONPATH}}" \
        "${NIM_DISCOVERY_PY}" -m discovery -o "${NIM_DISCOVERY_OUT}" "${@}"; }

# === PUBLIC ===

##! @function nim.discovery.run
##! @description full discovery pipeline from a stated idea / work request
##! @param <request>                 the request text, quoted
##! @param [-k|--keywords <a,b,c>]   explicit keywords (preferred over extraction)
##! @param [-p|--profile <name>]     prior profile (default|nim|bio; see nim.discovery.profiles)
##! @param [-r|--rigor <level>]      loose|standard|rigorous
##! @param [--pin <ontology>]        always select (repeatable)
##! @param [--exclude <ontology>]    never select (repeatable)
##! @output bundle in ${NIM_DISCOVERY_OUT}; progress on stderr
##! @return 0 on success, 1 on failure
##! @example nim.discovery.run "lab sample tracking" -k "sample, specimen, assay" -p bio
function nim.discovery.run() {
    nim.fn.validate.args "${@}" || return 1
    .nim.discovery.py.fn run "${@}" || { nim.out.fail "discovery: run failed"; return 1; }
    nim.out.ok "discovery: bundle at ${NIM_DISCOVERY_OUT}/BUNDLE.md"; }

##! @function nim.discovery.rerun
##! @description re-run from a stage after hand-editing request.json or selection.json
##! @param <stage>         search|select|merge
##! @return 0 on success, 1 on failure
##! @example nim.discovery.rerun select
function nim.discovery.rerun() {
    nim.fn.validate.args "${@}" || return 1
    nim.validate.enum "${1}" search select merge || return 1
    .nim.discovery.py.fn "${1}"; }

##! @function nim.discovery.show
##! @description print the bundle digest (BUNDLE.md)
##! @output markdown on stdout
function nim.discovery.show() { .nim.discovery.py.fn show; }

##! @function nim.discovery.check
##! @description validate bundle files against schema/bundle.schema.json and manifest hashes
##! @return 0 if valid, 1 otherwise
function nim.discovery.check() { .nim.discovery.py.fn check; }

##! @function nim.discovery.keywords
##! @description preview keywords extracted from a request (no network)
##! @param <request>       the request text, quoted
##! @output one keyword per line
function nim.discovery.keywords() {
    nim.fn.validate.args "${@}" || return 1
    .nim.discovery.py.fn keywords "${1}"; }

##! @function nim.discovery.profiles
##! @description list prior profiles from etc/sources.json
function nim.discovery.profiles() { .nim.discovery.py.fn profiles; }

##! @function nim.discovery.status
##! @description report whether the current project has a discovery bundle
##! @output one status line
##! @return 0 if a bundle exists, 1 if not
function nim.discovery.status() {
    if [[ -r ${NIM_DISCOVERY_OUT}/BUNDLE.md ]]; then
        nim.out.ok "discovery: bundle present (${NIM_DISCOVERY_OUT})"
        return 0
    fi
    nim.out.warn "discovery: no bundle in ${PWD}/${NIM_DISCOVERY_OUT}"
    return 1; }
