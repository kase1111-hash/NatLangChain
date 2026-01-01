{{/*
Expand the name of the chart.
*/}}
{{- define "natlangchain.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "natlangchain.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "natlangchain.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "natlangchain.labels" -}}
helm.sh/chart: {{ include "natlangchain.chart" . }}
{{ include "natlangchain.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "natlangchain.selectorLabels" -}}
app.kubernetes.io/name: {{ include "natlangchain.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "natlangchain.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "natlangchain.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the proper image name
*/}}
{{- define "natlangchain.image" -}}
{{- $registryName := .Values.image.registry -}}
{{- $repositoryName := .Values.image.repository -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{- if $registryName }}
{{- printf "%s/%s:%s" $registryName $repositoryName $tag -}}
{{- else }}
{{- printf "%s:%s" $repositoryName $tag -}}
{{- end }}
{{- end }}

{{/*
Return the Redis host
*/}}
{{- define "natlangchain.redisHost" -}}
{{- if .Values.redis.external.enabled }}
{{- .Values.redis.external.host }}
{{- else if .Values.redis.enabled }}
{{- printf "%s-redis-master" (include "natlangchain.fullname" .) }}
{{- else }}
{{- fail "Redis is required. Enable redis.enabled or redis.external.enabled" }}
{{- end }}
{{- end }}

{{/*
Return the Redis port
*/}}
{{- define "natlangchain.redisPort" -}}
{{- if .Values.redis.external.enabled }}
{{- .Values.redis.external.port | default 6379 }}
{{- else }}
{{- 6379 }}
{{- end }}
{{- end }}

{{/*
Return the Redis password secret name
*/}}
{{- define "natlangchain.redisSecretName" -}}
{{- if .Values.redis.external.existingSecret }}
{{- .Values.redis.external.existingSecret }}
{{- else if .Values.redis.external.enabled }}
{{- printf "%s-redis-external" (include "natlangchain.fullname" .) }}
{{- else }}
{{- printf "%s-redis" (include "natlangchain.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL host
*/}}
{{- define "natlangchain.postgresqlHost" -}}
{{- if .Values.postgresql.external.enabled }}
{{- .Values.postgresql.external.host }}
{{- else if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "natlangchain.fullname" .) }}
{{- else }}
{{- "" }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL port
*/}}
{{- define "natlangchain.postgresqlPort" -}}
{{- if .Values.postgresql.external.enabled }}
{{- .Values.postgresql.external.port | default 5432 }}
{{- else }}
{{- 5432 }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL database
*/}}
{{- define "natlangchain.postgresqlDatabase" -}}
{{- if .Values.postgresql.external.enabled }}
{{- .Values.postgresql.external.database | default "natlangchain" }}
{{- else }}
{{- .Values.postgresql.auth.database | default "natlangchain" }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL username
*/}}
{{- define "natlangchain.postgresqlUsername" -}}
{{- if .Values.postgresql.external.enabled }}
{{- .Values.postgresql.external.username | default "natlangchain" }}
{{- else }}
{{- .Values.postgresql.auth.username | default "natlangchain" }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL password secret name
*/}}
{{- define "natlangchain.postgresqlSecretName" -}}
{{- if .Values.postgresql.external.existingSecret }}
{{- .Values.postgresql.external.existingSecret }}
{{- else if .Values.postgresql.external.enabled }}
{{- printf "%s-postgresql-external" (include "natlangchain.fullname" .) }}
{{- else }}
{{- printf "%s-postgresql" (include "natlangchain.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return the app secret name
*/}}
{{- define "natlangchain.appSecretName" -}}
{{- if .Values.existingSecrets.appSecret }}
{{- .Values.existingSecrets.appSecret }}
{{- else }}
{{- printf "%s-app" (include "natlangchain.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Generate a random secret key
*/}}
{{- define "natlangchain.generateSecretKey" -}}
{{- randAlphaNum 64 | b64enc }}
{{- end }}
