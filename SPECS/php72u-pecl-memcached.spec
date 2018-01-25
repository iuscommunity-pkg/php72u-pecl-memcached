# IUS spec file for php72u-pecl-memcached, forked from
#
# Fedora spec file for php-pecl-memcached
#
# Copyright (c) 2009-2017 Remi Collet
# License: CC-BY-SA
# http://creativecommons.org/licenses/by-sa/4.0/
#
# Please, preserve the changelog entries
#

%global with_zts    0%{!?_without_zts:%{?__ztsphp:1}}
%global with_tests  0%{!?_without_tests:1}
%global pecl_name   memcached
# After 40-igbinary, 40-json, 40-msgpack
%global ini_name    50-%{pecl_name}.ini
%global php         php72u

%bcond_with msgpack

Summary:      Extension to work with the Memcached caching daemon
Name:         %{php}-pecl-%{pecl_name}
Version:      3.0.4
Release:      1.ius%{?dist}
License:      PHP
Group:        Development/Languages
URL:          http://pecl.php.net/package/%{pecl_name}

Source0:      http://pecl.php.net/get/%{pecl_name}-%{version}.tgz

BuildRequires: pecl >= 1.10.0
BuildRequires: %{php}-devel
BuildRequires: %{php}-json
BuildRequires: %{php}-pecl-igbinary-devel
%{?with_msgpack:BuildRequires: %{php}-pecl-msgpack-devel}
BuildRequires: libevent-devel  > 2
BuildRequires: libmemcached-devel >= 1.0.16
BuildRequires: zlib-devel
BuildRequires: cyrus-sasl-devel
BuildRequires: fastlz-devel
%if %{with_tests}
BuildRequires: memcached
%endif

Requires(post): pecl >= 1.10.0
Requires(postun): pecl >= 1.10.0
Requires:     %{php}-json%{?_isa}
Requires:     %{php}-pecl-igbinary%{?_isa}
Requires:     php(zend-abi) = %{php_zend_api}
Requires:     php(api) = %{php_core_api}
%{?with_msgpack:Requires: %{php}-msgpack%{?_isa}}

# provide the stock name
Provides:     php-pecl-%{pecl_name} = %{version}
Provides:     php-pecl-%{pecl_name}%{?_isa} = %{version}

# provide the stock and IUS names without pecl
Provides:     php-%{pecl_name} = %{version}
Provides:     php-%{pecl_name}%{?_isa} = %{version}
Provides:     %{php}-%{pecl_name} = %{version}
Provides:     %{php}-%{pecl_name}%{?_isa} = %{version}

# provide the stock and IUS names in pecl() format
Provides:     php-pecl(%{pecl_name}) = %{version}
Provides:     php-pecl(%{pecl_name})%{?_isa} = %{version}
Provides:     %{php}-pecl(%{pecl_name}) = %{version}
Provides:     %{php}-pecl(%{pecl_name})%{?_isa} = %{version}

# conflict with the stock name
Conflicts:    php-pecl-%{pecl_name} < %{version}

%{?filter_provides_in: %filter_provides_in %{php_extdir}/.*\.so$}
%{?filter_provides_in: %filter_provides_in %{php_ztsextdir}/.*\.so$}
%{?filter_setup}



%description
This extension uses libmemcached library to provide API for communicating
with memcached servers.

memcached is a high-performance, distributed memory object caching system,
generic in nature, but intended for use in speeding up dynamic web
applications by alleviating database load.

It also provides a session handler (memcached).


%prep
%setup -c -q
mv %{pecl_name}-%{version}%{?prever} NTS

# Don't install/register tests
sed -e 's/role="test"/role="src"/' \
    -e '/LICENSE/s/role="doc"/role="src"/' \
    -e '/name=.fastlz/d' \
    -i package.xml

rm -r NTS/fastlz

pushd NTS

# Check version as upstream often forget to update this
extver=$(sed -n '/#define PHP_MEMCACHED_VERSION/{s/.* "//;s/".*$//;p}' php_memcached.h)
if test "x${extver}" != "x%{version}%{?gh_date:-dev}%{?intver}"; then
   : Error: Upstream HTTP version is now ${extver}, expecting %{version}.
   : Update the pdover macro and rebuild.
   exit 1
fi
popd

cat > %{ini_name} << 'EOF'
; Enable %{pecl_name} extension module
extension=%{pecl_name}.so

; ----- Options to use the memcached session handler

; RPM note : save_handler and save_path are defined
; for mod_php, in /etc/httpd/conf.d/php.conf
; for php-fpm, in /etc/php-fpm.d/*conf

;  Use memcache as a session handler
;session.save_handler=memcached
;  Defines a comma separated list of server urls to use for session storage
;session.save_path="localhost:11211"

; ----- Configuration options
; http://php.net/manual/en/memcached.configuration.php

EOF

# default options with description from upstream
cat NTS/memcached.ini >>%{ini_name}

# Disable binary protocol by default to avoid warnings for libmemcached 1.0.16.
# See https://github.com/php-memcached-dev/php-memcached/issues/310 for more information.
sed -e '/^memcached.sess_binary_protocol = / s|On|Off|' -i %{ini_name}

%if %{with_zts}
cp -r NTS ZTS
%endif


%build
peclconf() {
%configure --enable-memcached-igbinary \
           --enable-memcached-json \
           --enable-memcached-sasl \
%{?with_msgpack: --enable-memcached-msgpack} \
           --enable-memcached-protocol \
           --with-system-fastlz \
           --with-php-config=$1
}
pushd NTS
%{_bindir}/phpize
peclconf %{_bindir}/php-config
make %{?_smp_mflags}
popd

%if %{with_zts}
pushd ZTS
%{_bindir}/zts-phpize
peclconf %{_bindir}/zts-php-config
make %{?_smp_mflags}
popd
%endif


%install
# Install the NTS extension
make install -C NTS INSTALL_ROOT=%{buildroot}

# Drop in the bit of configuration
# rename to z-memcached to be load after msgpack
install -D -m 644 %{ini_name} %{buildroot}%{php_inidir}/%{ini_name}

# Install XML package description
install -D -m 644 package.xml %{buildroot}%{pecl_xmldir}/%{pecl_name}.xml

# Install the ZTS extension
%if %{with_zts}
make install -C ZTS INSTALL_ROOT=%{buildroot}
install -D -m 644 %{ini_name} %{buildroot}%{php_ztsinidir}/%{ini_name}
%endif

# Documentation
pushd NTS
for i in $(grep 'role="doc"' ../package.xml | sed -e 's/^.*name="//;s/".*$//')
do install -Dpm 644 $i %{buildroot}%{pecl_docdir}/%{pecl_name}/$i
done
popd


%check
OPT="-n"
[ -f %{php_extdir}/igbinary.so ] && OPT="$OPT -d extension=igbinary.so"
[ -f %{php_extdir}/json.so ]     && OPT="$OPT -d extension=json.so"
[ -f %{php_extdir}/msgpack.so ]  && OPT="$OPT -d extension=msgpack.so"

: Minimal load test for NTS extension
%{__php} $OPT \
    -d extension=%{buildroot}%{php_extdir}/%{pecl_name}.so \
    --modules | grep %{pecl_name}

%if %{with_zts}
: Minimal load test for ZTS extension
%{__ztsphp} $OPT \
    -d extension=%{buildroot}%{php_ztsextdir}/%{pecl_name}.so \
    --modules | grep %{pecl_name}
%endif

%if %{with_tests}
# XFAIL and very slow so no value
rm ?TS/tests/expire.phpt

ret=0

: Launch the Memcached service
port=$(%{__php} -r 'echo 10000 + PHP_MAJOR_VERSION*100 + PHP_MINOR_VERSION*10 + PHP_INT_SIZE;')
memcached -p $port -U $port      -d -P $PWD/memcached.pid
sed -e "s/11211/$port/" -i ?TS/tests/*

: Run the upstream test Suite for NTS extension
pushd NTS
rm tests/flush_buffers.phpt tests/touch_binary.phpt
TEST_PHP_EXECUTABLE=%{__php} \
TEST_PHP_ARGS="$OPT -d extension=$PWD/modules/%{pecl_name}.so" \
NO_INTERACTION=1 \
REPORT_EXIT_STATUS=1 \
%{__php} -n run-tests.php --show-diff || ret=1
popd

%if %{with_zts}
: Run the upstream test Suite for ZTS extension
pushd ZTS
rm tests/flush_buffers.phpt tests/touch_binary.phpt
TEST_PHP_EXECUTABLE=%{__ztsphp} \
TEST_PHP_ARGS="$OPT -d extension=$PWD/modules/%{pecl_name}.so" \
NO_INTERACTION=1 \
REPORT_EXIT_STATUS=1 \
%{__ztsphp} -n run-tests.php --show-diff || ret=1
popd
%endif

# Cleanup
if [ -f memcached.pid ]; then
   kill $(cat memcached.pid)
fi

exit $ret
%endif


%post
%{pecl_install} %{pecl_xmldir}/%{pecl_name}.xml >/dev/null || :


%postun
if [ $1 -eq 0 ]; then
    %{pecl_uninstall} %{pecl_name} >/dev/null || :
fi

%files
%license NTS/LICENSE
%doc %{pecl_docdir}/%{pecl_name}
%{pecl_xmldir}/%{pecl_name}.xml

%config(noreplace) %{php_inidir}/%{ini_name}
%{php_extdir}/%{pecl_name}.so

%if %{with_zts}
%config(noreplace) %{php_ztsinidir}/%{ini_name}
%{php_ztsextdir}/%{pecl_name}.so
%endif


%changelog
* Thu Jan 25 2018 Ben Harper <ben.harper@rackspace.com> - 3.0.4-1.ius
- port from fedora

* Tue Nov 21 2017 Remi Collet <remi@remirepo.net> - 3.0.4-1
- Update to 3.0.4

* Tue Oct 03 2017 Remi Collet <remi@fedoraproject.org> - 3.0.3-4
- rebuild for https://fedoraproject.org/wiki/Changes/php72

* Thu Aug 03 2017 Fedora Release Engineering <releng@fedoraproject.org> - 3.0.3-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 3.0.3-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Mon Feb 20 2017 Remi Collet <remi@fedoraproject.org> - 3.0.3-1
- update to 3.0.3 (php 7, stable)
- build with --enable-memcached-protocol option

* Mon Feb 13 2017 Remi Collet <remi@fedoraproject.org> - 3.0.2-1
- update to 3.0.2 (php 7, stable)

* Thu Feb  9 2017 Remi Collet <remi@fedoraproject.org> - 3.0.1-1
- update to 3.0.1 (php 7, stable)
- switch to pecl sources
- enable test suite
- open https://github.com/php-memcached-dev/php-memcached/pull/319
  fix test suite for 32bits build

* Mon Nov 14 2016 Remi Collet <remi@fedoraproject.org> - 3.0.0-0.2.20160217git6ace07d
- rebuild for https://fedoraproject.org/wiki/Changes/php71

* Mon Jun 27 2016 Remi Collet <rcollet@redhat.com> - 3.0.0-0.1.20160217git6ace07d
- git snapshopt for PHP 7
- don't install/register tests
- fix license installation

* Wed Feb 10 2016 Remi Collet <remi@fedoraproject.org> - 2.2.0-8
- drop scriptlets (replaced by file triggers in php-pear)
- cleanup

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 2.2.0-7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.0-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Sun Aug 17 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.0-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Thu Jun 19 2014 Remi Collet <rcollet@redhat.com> - 2.2.0-4
- rebuild for https://fedoraproject.org/wiki/Changes/Php56

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Thu Apr 24 2014 Remi Collet <rcollet@redhat.com> - 2.2.0-2
- add numerical prefix to extension configuration file

* Wed Apr  2 2014  Remi Collet <remi@fedoraproject.org> - 2.2.0-1
- update to 2.2.0 (stable)
- add all ini options in configuration file (comments)
- install doc in pecl doc_dir
- install tests in pecl test_dir
- add dependency on pecl/msgpack (except on ppc64)
- add --with tests option to run upstream test suite during build

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.1.0-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Fri Mar 22 2013 Remi Collet <rcollet@redhat.com> - 2.1.0-7
- rebuild for http://fedoraproject.org/wiki/Features/Php55

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.1.0-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Mon Nov 19 2012  Remi Collet <remi@fedoraproject.org> - 2.1.0-5
- requires libmemcached >= build version

* Sat Nov 17 2012  Remi Collet <remi@fedoraproject.org> - 2.1.0-4
- rebuild for libmemcached 1.0.14 (with SASL)
- switch to upstream patch
- add patch to report about SASL support in phpinfo

* Fri Oct 19 2012 Remi Collet <remi@fedoraproject.org> - 2.1.0-3
- improve comment in configuration about session.

* Sat Sep 22 2012 Remi Collet <remi@fedoraproject.org> - 2.1.0-2
- rebuild for new libmemcached
- drop sasl support

* Tue Aug 07 2012 Remi Collet <remi@fedoraproject.org> - 2.1.0-1
- update to 2.1.0
- add patch to lower libmemcached required version

* Tue Jul 31 2012 Remi Collet <remi@fedoraproject.org> - 2.0.1-4
- bump release

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Mon Apr 23 2012  Remi Collet <remi@fedoraproject.org> - 2.0.1-3
- enable ZTS extension

* Sat Mar 03 2012  Remi Collet <remi@fedoraproject.org> - 2.0.1-1
- update to 2.0.1

* Sat Mar 03 2012  Remi Collet <remi@fedoraproject.org> - 2.0.0-1
- update to 2.0.0

* Thu Jan 19 2012 Remi Collet <remi@fedoraproject.org> - 2.0.0-0.1.1736623
- update to git snapshot (post 2.0.0b2) for php 5.4 build

* Sat Jan 14 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.2-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Sat Sep 17 2011  Remi Collet <remi@fedoraproject.org> - 1.0.2-7
- rebuild against libmemcached 0.52
- adapted filter
- clean spec

* Thu Jun 02 2011  Remi Collet <Fedora@FamilleCollet.com> - 1.0.2-6
- rebuild against libmemcached 0.49

* Thu Mar 17 2011  Remi Collet <Fedora@FamilleCollet.com> - 1.0.2-5
- rebuilt with igbinary support
- add arch specific provides/requires

* Wed Feb 09 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.2-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Sat Oct 23 2010  Remi Collet <Fedora@FamilleCollet.com> - 1.0.2-3
- add filter_provides to avoid private-shared-object-provides memcached.so

* Fri Oct 01 2010 Remi Collet <fedora@famillecollet.com> - 1.0.2-2
- rebuild against libmemcached 0.44 with SASL support

* Tue May 04 2010 Remi Collet <fedora@famillecollet.com> - 1.0.2-1
- update to 1.0.2 for libmemcached 0.40

* Sat Mar 13 2010 Remi Collet <fedora@famillecollet.com> - 1.0.1-1
- update to 1.0.1 for libmemcached 0.38

* Sun Feb 07 2010 Remi Collet <fedora@famillecollet.com> - 1.0.0-3.1
- bump release

* Sat Feb 06 2010 Remi Collet <fedora@famillecollet.com> - 1.0.0-3
- rebuilt against new libmemcached
- add minimal %%check

* Sun Jul 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Sun Jul 12 2009 Remi Collet <fedora@famillecollet.com> - 1.0.0-1
- Update to 1.0.0 (First stable release)

* Sat Jun 27 2009 Remi Collet <fedora@famillecollet.com> - 0.2.0-1
- Update to 0.2.0 + Patch for HAVE_JSON constant

* Wed Apr 29 2009 Remi Collet <fedora@famillecollet.com> - 0.1.5-1
- Initial RPM

