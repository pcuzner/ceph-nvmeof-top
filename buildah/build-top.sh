#!/usr/bin/bash

if [ ! -z "$1" ]; then
  TAG=$1
else
  TAG='latest'
fi

echo "Building Alpine Linux based image with the tag: $TAG"

IMAGE="alpine:edge"

container=$(buildah from $IMAGE)
buildah run $container apk add python3
buildah run $container apk add py3-setuptools
buildah run $container apk add py3-yaml
buildah run $container apk add py3-grpcio --repository http://dl-cdn.alpinelinux.org/alpine/edge/community/
buildah run $container apk add py3-protobuf --repository http://dl-cdn.alpinelinux.org/alpine/edge/community/
buildah run $container apk add py3-regex --repository http://dl-cdn.alpinelinux.org/alpine/edge/community/
buildah run $container apk add py3-urwid --repository http://dl-cdn.alpinelinux.org/alpine/edge/community/

buildah run $container mkdir -p /nvmeof-top/nvmeof_top
buildah copy $container ../nvmeof_top /nvmeof-top/nvmeof_top
buildah copy $container ../nvmeof-top.py /nvmeof-top/nvmeof-top.py
buildah run $container chmod ug+x /nvmeof-top/nvmeof-top.py

# finalize
buildah config --env PS1="[nvmeof-top] \w\$ " $container
buildah config --env TERM="xterm-256color" $container
buildah config --workingdir /nvmeof-top $container
buildah config --entrypoint '["python3", "./nvmeof-top.py"]' $container
buildah config --cmd '["-h"]' $container


buildah config --label maintainer="Paul Cuzner <pcuzner@redhat.com>" $container
buildah config --label description="nvmeof top tool for subsystem performance monitoring" $container
buildah config --label summary="CLI based nvmeof performance monitoring" $container
buildah commit --format docker --squash $container nvmeof-top:$TAG