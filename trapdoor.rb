class Trapdoor < Formula
  desc "Give cloud AIs safe access to your local machine (with access tiers)"
  homepage "https://github.com/patricksomerville/trapdoor-1.0"
  url "https://github.com/patricksomerville/trapdoor-1.0/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "b2823577c693778b0a7f0ec067cb5f5d25f8f06da01ce93c3f12bf3e27289318"
  license "MIT"

  depends_on "python@3.12"

  def install
    venv = virtualenv_create(libexec, "python3")
    venv.pip_install buildpath
    (bin/"trapdoor").write_env_script(libexec/"bin/trapdoor", {})
  end

  test do
    assert_match "Trapdoor", shell_output("#{bin}/trapdoor --help")
  end
end
