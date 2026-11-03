# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present Team CoreELEC (https://coreelec.org)

# hyperion.ng as a dependency would also install its /usr/share/hyperion tree into the image
. $(get_pkg_directory hyperion.ng)/package.mk

PKG_NAME="hyperion.canary"
PKG_URL=""
PKG_DEPENDS_UNPACK+=" hyperion.ng"

PKG_IS_ADDON="embedded"
PKG_ADDON_IS_STANDALONE="yes"
PKG_ADDON_NAME="Hyperion.NG (canary)"

unpack() {
  mkdir -p ${PKG_BUILD}
  tar --strip-components=1 -xf ${SOURCES}/hyperion.ng/hyperion.ng-${PKG_VERSION}.tar.gz -C ${PKG_BUILD}
}

makeinstall_target() {
  local addon_dir="${INSTALL}/usr/share/kodi/addons/${PKG_ADDON_ID}"

  ADDON_BUILD="${INSTALL}/usr/share/kodi/addons" addon
  PKG_DIR="$(get_pkg_directory hyperion.ng)" install_addon_files "${addon_dir}"

  rm -r "${addon_dir}/system.d"
  mv "${addon_dir}/default.py" "${addon_dir}/feeder.py"
  sed -e "s/service\.hyperion\.ng/${PKG_ADDON_ID}/g" \
      -i "${addon_dir}/feeder.py" \
         "${addon_dir}/resources/settings.xml" \
         "${addon_dir}/resources/language/resource.language.en_gb/strings.po"
  install_addon_source "${addon_dir}"
}
