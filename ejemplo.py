  const projects = useProjectsStore()
  const files = ref<ProjectFile[]>([])
  const uploading = ref(false)
  const status = ref('')
  const error = ref('')
  const pendingName = ref('')
  let pending: { projectId: string; file: File; signed?: SignedFile; uploaded: boolean } | undefined
  let request: AbortController | undefined
  let listing: AbortController | undefined
  async function refresh(projectId: string) {
    listing?.abort()
    const current = new AbortController()
    listing = current
    try {
      const result = await listFiles(projectId, current.signal)
      if (!current.signal.aborted && projects.active?.id === projectId) files.value = result
    } catch (failure) {
      if (!current.signal.aborted && projects.active?.id === projectId)
        error.value =
          failure instanceof ApiError ? failure.message : 'No se pudieron consultar los archivos.'
    }
  }
  async function process() {
    const work = pending
    if (!work || uploading.value || projects.active?.id !== work.projectId) return
    const current = new AbortController()
    request = current
    uploading.value = true
    error.value = ''
    try {
      if (!work.signed) {
        status.value = 'Preparando archivo…'
        work.signed = await signFile(work.projectId, work.file, current.signal)
      }
      if (!work.uploaded) {
        status.value = 'Subiendo archivo…'
        await uploadFile(work.projectId, work.signed.id, work.file, current.signal)
        work.uploaded = true
      }
      status.value = 'Vectorizando y guardando en PostgreSQL… Puede tardar unos minutos.'
      const result = await indexFile(work.projectId, work.signed.url, current.signal)
      if (current.signal.aborted || projects.active?.id !== work.projectId) return
      listing?.abort()
      files.value = files.value.filter((item) => item.id !== result.id)
      files.value.push({
        id: result.id,
        name: result.nombre,
        chunks: result.chunks,
        indexedAtUtc: result.indexedAtUtc,
      })
      status.value = `${result.nombre}: listo para consultar con MÍA.`
      pending = undefined
      pendingName.value = ''
    } catch (failure) {
      if (current.signal.aborted) return
      status.value = ''
      error.value =
        failure instanceof ApiError ? failure.message : 'No se pudo procesar el archivo. Reintenta.'
    } finally {
      if (request === current) {
        request = undefined
        uploading.value = false
      }
    }