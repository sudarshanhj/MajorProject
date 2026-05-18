const fs = require('fs');
const files = {
  'src/main.tsx': "import React from 'react'",
  'src/components/DashboardLayout.tsx': "import { useState } from 'react'",
  'src/pages/Admin.tsx': "import { useState, useEffect } from 'react'",
  'src/pages/Analyze.tsx': "import { useState, useCallback, Suspense } from 'react'",
  'src/pages/Batch.tsx': "import { useState, useCallback } from 'react'",
  'src/pages/Embed.tsx': "import { useState, useCallback } from 'react'",
  'src/pages/Extract.tsx': "import { useState, useCallback } from 'react'",
  'src/pages/Overview.tsx': "import { useState } from 'react'"
};
for (const [file, imp] of Object.entries(files)) {
  const content = fs.readFileSync(file, 'utf8').split('\n');
  content[0] = imp;
  fs.writeFileSync(file, content.join('\n'));
}
