FROM alpine:latest

ARG key1
ARG key2=def
ENV key1="${key1}"

RUN for i in 1 2 3 5; \
    do \
        echo $i; \
    done; \
    echo "finish"