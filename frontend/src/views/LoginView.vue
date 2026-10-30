<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useSession } from "../stores/session";
import { useAction } from "../composables/actions";
import AppIcon from "../components/AppIcon.vue";
const username = ref("admin"),
  password = ref(""),
  router = useRouter(),
  route = useRoute(),
  session = useSession();
const { busy, error, run } = useAction();
async function submit() {
  await run(async () => {
    await session.login(username.value, password.value);
    const redirect = String(route.query.redirect || "");
    await router.replace(
      redirect.startsWith("/") &&
        !redirect.startsWith("//") &&
        !redirect.startsWith("/login")
        ? redirect
        : "/projects",
    );
  });
}
</script>
<template>
  <div class="login">
    <section class="login-intro">
      <div class="brand">
        <span class="brand-symbol"><AppIcon name="globe" :size="29" /></span
        ><span
          >Terra<span class="brand-light">Scope</span
          ><small>洪灾道路调查平台</small></span
        >
      </div>
      <div class="login-copy">
        <span class="eyebrow">OBSERVE · ANALYSE · VERIFY</span>
        <h1>从影像洞察，<br />到调查决策。</h1>
        <p>连接影像、模型与人工判读，为洪灾道路调查提供可追溯的分析依据。</p>
        <div class="login-points">
          <span>影像解译</span><span>协同复核</span><span>证据追踪</span>
        </div>
      </div>
      <span class="login-foot">TERRASCOPE / FLOOD INTELLIGENCE PLATFORM</span>
    </section>
    <div class="login-form-area">
      <section class="panel">
        <span class="eyebrow muted">WELCOME TO TERRASCOPE</span>
        <h2>登录工作区</h2>
        <p class="muted">登录 TerraScope</p>
        <el-form label-position="top" @submit.prevent="submit"
          ><el-form-item label="用户名"
            ><el-input
              v-model="username"
              autocomplete="username"
              aria-label="用户名" /></el-form-item
          ><el-form-item label="密码"
            ><el-input
              v-model="password"
              type="password"
              show-password
              autocomplete="current-password"
              aria-label="密码"
          /></el-form-item>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <el-button
            native-type="submit"
            type="primary"
            :loading="busy"
            style="width: 100%"
            >登录</el-button
          ></el-form
        >
      </section>
    </div>
  </div>
</template>
