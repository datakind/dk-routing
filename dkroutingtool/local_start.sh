docker run -it \
  --mount src=`pwd`/src,target=/src,type=bind \
  --mount src=`pwd`/scripts,target=/scripts,type=bind \
  -p 8080:8080 \
  -p 5001:5001 \
  dkroutingtool:dev bash

