{{/*
Expand the name of the chart.
*/}}
{{- define "${{ values.componentId }}.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "${{ values.componentId }}.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Create chart label.
*/}}
{{- define "${{ values.componentId }}.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "${{ values.componentId }}.labels" -}}
helm.sh/chart: {{ include "${{ values.componentId }}.chart" . }}
{{ include "${{ values.componentId }}.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
backstage.io/kubernetes-id: ${{ values.componentId }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "${{ values.componentId }}.selectorLabels" -}}
app.kubernetes.io/name: {{ include "${{ values.componentId }}.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name.
*/}}
{{- define "${{ values.componentId }}.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "${{ values.componentId }}.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
