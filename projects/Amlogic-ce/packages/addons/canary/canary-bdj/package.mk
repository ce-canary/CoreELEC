# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present Team CoreELEC (https://coreelec.org)

# jre-libbluray as a dependency would also install its libbluray.so into the image
. $(get_pkg_directory jre-libbluray)/package.mk

PKG_NAME="canary-bdj"
PKG_NEED_UNPACK+=" $(get_pkg_directory jre-libbluray)"
PKG_LONGDESC="libbluray jars of this image for the BD-J menus, run by the stock tools.jre.zulu"

unpack() {
  mkdir -p ${PKG_BUILD}
  tar --strip-components=1 -xf ${SOURCES}/libbluray/libbluray-${PKG_VERSION}.tar.xz -C ${PKG_BUILD}
}

post_makeinstall_target() {
  rm -rf ${INSTALL}/usr/lib ${INSTALL}/usr/include
}
