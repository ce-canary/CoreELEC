# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present Team CoreELEC (https://coreelec.org)

# the add-on keeps its id, as items name it in their inputstream property
. $(get_pkg_directory inputstream.adaptive)/package.mk

PKG_NAME="inputstream.adaptive.canary"
PKG_URL=""
PKG_DEPENDS_UNPACK+=" inputstream.adaptive"
PKG_IS_ADDON="embedded"

unpack() {
  mkdir -p ${PKG_BUILD}
  tar --strip-components=1 -xf ${SOURCES}/inputstream.adaptive/inputstream.adaptive-${PKG_VERSION}.tar.gz -C ${PKG_BUILD}
}

# above the repository's <version>.<rev>, so Kodi loads this copy while both are installed
post_makeinstall_target() {
  local addon_xml="${INSTALL}/usr/share/kodi/addons/inputstream.adaptive/addon.xml"
  local addon_version="$(xmlstarlet sel -t -v "/addon/@version" "${addon_xml}").1000"

  xmlstarlet ed --inplace -u "/addon/@version" -v "${addon_version}" "${addon_xml}"
}
