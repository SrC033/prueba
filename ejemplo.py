  const projects = useProjectsStore()
  const files = ref<ProjectFile[]>([])
  const uploading = ref(false)
  