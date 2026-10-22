# Fetch named secrets from Doppler into the environment of a Spacelift run.
#
# Usage, from a Spacelift hook (see .spacelift/config.yml), as two commands:
#
#   . /mnt/workspace/source/scripts/spacelift/doppler-env.sh
#   cah_doppler_env ARG [ARG ...]
#
# Each ARG is either NAME (fetch NAME from Doppler, export it as NAME) or
# VAR=NAME (fetch NAME from Doppler, export it as VAR). The second form exists
# because Doppler only allows uppercase secret names, while OpenTofu reads a
# variable named foo only from the exact environment variable TF_VAR_foo.
#
# It is sourced, not executed, so the exported variables reach the phase that
# follows. Sourcing only defines functions: arguments to a sourced file are not
# portable (dash ignores them), so the call is a separate command. POSIX sh
# only: the Spacelift runner image is Alpine (busybox ash).
#
# What it does, in order:
#   1. Skips unless the run is allowed to hold credentials (see below).
#   2. Checks the Doppler settings that the Spacelift context provides.
#   3. Installs the pinned Doppler CLI, verified against a pinned SHA-256.
#   4. For each NAME, fetches it, exports it, and masks it in the run logs.
#
# Credentials are only fetched for a tracked or destroy run on the main branch.
# This repository is public, so a pull request (proposed run) must never see
# them: planning executes provider and data-source code from the pull request.
#
# Needs DOPPLER_TOKEN (a read-only service token, secret), DOPPLER_PROJECT and
# DOPPLER_CONFIG, all from the cah-doppler Spacelift context.
#
# To change the pinned CLI, follow docs/spacelift-secrets.md.

CAH_DOPPLER_VERSION="3.77.0"
CAH_DOPPLER_SHA256_AMD64="92587cb89c2ff82fc2ddec2b2a9f275ff320994a44e16cd9310b55a429a82084"
CAH_DOPPLER_SHA256_ARM64="3aa603d60bc8502ec67d9a57e917925f357ac2822eead484acda3875fe6a4d95"
# CAH_DOPPLER_DIR is optional. When it is not set, a new private folder is made
# with mktemp -d (never a fixed name in the shared /tmp, where another local user
# could plant the file this script then runs).

cah_doppler_log() {
  printf 'doppler-env: %s\n' "$*"
}

# Prints the name of the first failure and returns non-zero.
cah_doppler_install() {
  _arch=$(uname -m)
  case "$_arch" in
    x86_64 | amd64) _arch=amd64 _sha=$CAH_DOPPLER_SHA256_AMD64 ;;
    aarch64 | arm64) _arch=arm64 _sha=$CAH_DOPPLER_SHA256_ARM64 ;;
    *)
      cah_doppler_log "unsupported architecture: $_arch"
      return 1
      ;;
  esac

  if command -v doppler >/dev/null 2>&1 &&
    [ "$(doppler --version 2>/dev/null | sed 's/^v//')" = "$CAH_DOPPLER_VERSION" ]; then
    return 0
  fi

  _tar="doppler_${CAH_DOPPLER_VERSION}_linux_${_arch}.tar.gz"
  _url="https://github.com/DopplerHQ/cli/releases/download/${CAH_DOPPLER_VERSION}/${_tar}"
  if [ -z "${CAH_DOPPLER_DIR:-}" ]; then
    CAH_DOPPLER_DIR=$(mktemp -d) || return 1
  else
    mkdir -p -m 700 "$CAH_DOPPLER_DIR" || return 1
  fi
  if [ -L "$CAH_DOPPLER_DIR" ] || [ ! -d "$CAH_DOPPLER_DIR" ] || [ ! -O "$CAH_DOPPLER_DIR" ]; then
    cah_doppler_log "refusing: $CAH_DOPPLER_DIR is a symlink, not a folder, or not yours"
    return 1
  fi

  if ! curl -fsSL --proto '=https' --tlsv1.2 --retry 3 -o "$CAH_DOPPLER_DIR/$_tar" "$_url"; then
    cah_doppler_log "download failed: $_url"
    return 1
  fi
  if ! printf '%s  %s\n' "$_sha" "$CAH_DOPPLER_DIR/$_tar" | sha256sum -c - >/dev/null 2>&1; then
    cah_doppler_log "checksum mismatch for $_tar; refusing to run it"
    rm -f "$CAH_DOPPLER_DIR/$_tar"
    return 1
  fi
  tar -xzf "$CAH_DOPPLER_DIR/$_tar" -C "$CAH_DOPPLER_DIR" doppler || return 1
  rm -f "$CAH_DOPPLER_DIR/$_tar"
  PATH="$CAH_DOPPLER_DIR:$PATH"
  export PATH
}

cah_doppler_env() {
  _run_type="${TF_VAR_spacelift_run_type:-}"
  _branch="${TF_VAR_spacelift_commit_branch:-}"

  case "$_run_type" in
    TRACKED | DESTROY) ;;
    *)
      cah_doppler_log "run type '${_run_type:-unset}' does not get secrets; skipping"
      return 0
      ;;
  esac
  if [ "$_branch" != "main" ]; then
    cah_doppler_log "branch '${_branch:-unset}' is not main; skipping"
    return 0
  fi

  if [ "$#" -eq 0 ]; then
    cah_doppler_log "no secret names given"
    return 1
  fi
  for _arg in "$@"; do
    case "$_arg" in
      *=*) _var=${_arg%%=*} _src=${_arg#*=} ;;
      *) _var=$_arg _src=$_arg ;;
    esac
    for _n in "$_var" "$_src"; do
      case "$_n" in
        '' | [0-9]* | *[!A-Za-z0-9_]*)
          cah_doppler_log "invalid secret name: $_arg"
          return 1
          ;;
      esac
    done
  done

  for _var in DOPPLER_TOKEN DOPPLER_PROJECT DOPPLER_CONFIG; do
    eval "_val=\${$_var:-}"
    if [ -z "$_val" ]; then
      cah_doppler_log "$_var is not set; is the cah-doppler context attached?"
      return 1
    fi
  done

  cah_doppler_install || return 1

  for _arg in "$@"; do
    case "$_arg" in
      *=*) _var=${_arg%%=*} _src=${_arg#*=} ;;
      *) _var=$_arg _src=$_arg ;;
    esac
    if ! _val=$(doppler secrets get "$_src" --plain --no-check-version \
      --project "$DOPPLER_PROJECT" --config "$DOPPLER_CONFIG" 2>/dev/null); then
      cah_doppler_log "could not read $_src from Doppler"
      return 1
    fi
    if [ -z "$_val" ]; then
      cah_doppler_log "$_src is empty in Doppler"
      return 1
    fi
    echo "::add-mask $_val"
    export "$_var=$_val"
    cah_doppler_log "loaded $_src as $_var"
  done
  unset _val
}
