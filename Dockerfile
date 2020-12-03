FROM continuumio/miniconda3:4.9.2
LABEL maintainer="napiersk@isi.edu"

WORKDIR /aif/
RUN git clone https://github.com/NextCenturyCorporation/AIDA-Interchange-Format.git
WORKDIR /aif/AIDA-Interchange-Format/python/
RUN pip install .

WORKDIR /aida-viz/src/
COPY . .
RUN pip install .

CMD [ "/bin/bash", "" ]

# Variable substitution below DID NOT WORK.
#ENTRYPOINT [ "python" ]
#CMD [ "-m", "aida_viz", "-a", ${AIDA_AIF_TTL}, "-d", ${AIDA_CORPUS_SQLITE}, "-o", ${RESULTS} ]
