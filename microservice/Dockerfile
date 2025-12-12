FROM python:3.12-slim AS base

########################
# Install Dependencies #
########################

WORKDIR /app

# Install uv for faster package management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system -e .


###########
# Workdir #
###########

WORKDIR /app/src
ENV PYTHONPATH="${PYTHONPATH}:/app/src"


##############################
# Define Default Dev Command #
##############################

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8081"]


FROM base AS production

#############
# Copy Data #
#############

# Copy app source to container
COPY ./src /app/src


##########
# Verify #
##########

# Check content of app folder
RUN ls -la /app/src
RUN ls -la /app/src/scraper


#####################################
# Define Default Production Command #
#####################################

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
