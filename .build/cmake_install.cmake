# Install script for directory: /home/filipo/src/picongpu/include/picongpu

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/home/filipo/Fusion_Setups")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set default install directory permissions.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/home/filipo/Fusion_Setups/.build/build_nlohmann_json/cmake_install.cmake")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/picongpu" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/picongpu")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/picongpu"
         RPATH "\$ORIGIN:/home/filipo/spack/opt/spack/linux-skylake/libpng-1.6.47-lqg3lcftt6uhsycenqbwaygjkqra7qhq/lib:/home/filipo/spack/opt/spack/linux-skylake/zlib-ng-2.2.4-qx2j5xldovoeqrcmxqaubmengeeb66k3/lib:/home/filipo/spack/opt/spack/linux-skylake/freetype-2.14.1-axnc74qzammmax5tgimke5bhy4miybln/lib:/home/filipo/spack/opt/spack/linux-skylake/openpmd-api-0.16.1-mwp5qkf2eknsegvs5uwi3cxhzekji3wr/lib:/home/filipo/spack/opt/spack/linux-skylake/hdf5-1.14.6-s2bzi4hlxltkim567bb6fnvtmekf7ym6/lib:/home/filipo/spack/opt/spack/linux-skylake/adios2-2.11.0-dqf4d3jczypbfsul3yryrlf3qajl2kpj/lib:/home/filipo/spack/opt/spack/linux-skylake/boost-1.83.0-3zf6dwasjpcmu4moykwufzydnhl7wdzy/lib:/home/filipo/spack/opt/spack/linux-skylake/openmpi-4.1.5-w4464kcvil6qbs4q5pa5qddw7yonoclx/lib")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/bin" TYPE EXECUTABLE FILES "/home/filipo/Fusion_Setups/.build/picongpu")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/picongpu" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/picongpu")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/picongpu"
         OLD_RPATH "/home/filipo/spack/opt/spack/linux-skylake/libpng-1.6.47-lqg3lcftt6uhsycenqbwaygjkqra7qhq/lib:/home/filipo/spack/opt/spack/linux-skylake/zlib-ng-2.2.4-qx2j5xldovoeqrcmxqaubmengeeb66k3/lib:/home/filipo/spack/opt/spack/linux-skylake/freetype-2.14.1-axnc74qzammmax5tgimke5bhy4miybln/lib:/home/filipo/spack/opt/spack/linux-skylake/openpmd-api-0.16.1-mwp5qkf2eknsegvs5uwi3cxhzekji3wr/lib:/home/filipo/spack/opt/spack/linux-skylake/hdf5-1.14.6-s2bzi4hlxltkim567bb6fnvtmekf7ym6/lib:/home/filipo/spack/opt/spack/linux-skylake/adios2-2.11.0-dqf4d3jczypbfsul3yryrlf3qajl2kpj/lib:/home/filipo/spack/opt/spack/linux-skylake/boost-1.83.0-3zf6dwasjpcmu4moykwufzydnhl7wdzy/lib:/home/filipo/spack/opt/spack/linux-skylake/openmpi-4.1.5-w4464kcvil6qbs4q5pa5qddw7yonoclx/lib::::::::"
         NEW_RPATH "\$ORIGIN:/home/filipo/spack/opt/spack/linux-skylake/libpng-1.6.47-lqg3lcftt6uhsycenqbwaygjkqra7qhq/lib:/home/filipo/spack/opt/spack/linux-skylake/zlib-ng-2.2.4-qx2j5xldovoeqrcmxqaubmengeeb66k3/lib:/home/filipo/spack/opt/spack/linux-skylake/freetype-2.14.1-axnc74qzammmax5tgimke5bhy4miybln/lib:/home/filipo/spack/opt/spack/linux-skylake/openpmd-api-0.16.1-mwp5qkf2eknsegvs5uwi3cxhzekji3wr/lib:/home/filipo/spack/opt/spack/linux-skylake/hdf5-1.14.6-s2bzi4hlxltkim567bb6fnvtmekf7ym6/lib:/home/filipo/spack/opt/spack/linux-skylake/adios2-2.11.0-dqf4d3jczypbfsul3yryrlf3qajl2kpj/lib:/home/filipo/spack/opt/spack/linux-skylake/boost-1.83.0-3zf6dwasjpcmu4moykwufzydnhl7wdzy/lib:/home/filipo/spack/opt/spack/linux-skylake/openmpi-4.1.5-w4464kcvil6qbs4q5pa5qddw7yonoclx/lib")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/picongpu")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/bin" TYPE DIRECTORY FILES "/home/filipo/src/picongpu/include/picongpu/../../bin/" FILES_MATCHING REGEX "/[^/]*$" PERMISSIONS OWNER_EXECUTE OWNER_READ OWNER_WRITE GROUP_READ GROUP_EXECUTE REGEX "/\\.svn$" EXCLUDE)
endif()

if(CMAKE_INSTALL_COMPONENT)
  set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INSTALL_COMPONENT}.txt")
else()
  set(CMAKE_INSTALL_MANIFEST "install_manifest.txt")
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
file(WRITE "/home/filipo/Fusion_Setups/.build/${CMAKE_INSTALL_MANIFEST}"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
