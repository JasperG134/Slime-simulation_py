# slime_sim_gpu.py
"""
A Python-based GPU slime simulation (PyOpenGL + compute shaders).
Fixed so that 1 agent doesn't look huge, by lowering deposit & scaling it by agent count.
"""

import sys
import math
import random
import numpy as np

import glfw
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
from PIL import Image

import config

COMPUTE_SHADER_SOURCE = r"""
#version 430

layout(local_size_x=256, local_size_y=1) in;

struct Agent {
    float x;
    float y;
    float angle;
    float seed;
    int   species;
};

layout(std430, binding=0) buffer AgentsSSBO {
    Agent agents[];
};

layout(rgba32f, binding=0) uniform image2D trailMap;
layout(r8, binding=1)   uniform readonly image2D obstaclesTex;

uniform int   passType;
uniform float simWidth;
uniform float simHeight;
uniform bool  useObstacles;
uniform float evaporationFactor;
uniform int   blurRadius;

// For deposit scaling
uniform float depositScaleFactor; // e.g., if totalAgents=300k, we might do 300k / actual => etc.

// species arrays
const int MAX_SPECIES=4;
uniform int   numSpecies;
uniform float speeds[MAX_SPECIES];
uniform float turnSpeeds[MAX_SPECIES];
uniform float sensorAngles[MAX_SPECIES];
uniform float sensorDistances[MAX_SPECIES];
uniform float depositAmounts[MAX_SPECIES];

uniform float randomTurnFactor;

float rand(inout float seed) {
    seed = fract(seed*123.4567 + 0.98765);
    return seed;
}

bool isBlocked(float x, float y) {
    if(x<0.0||x>=simWidth||y<0.0||y>=simHeight) {
        return true;
    }
    ivec2 coord=ivec2(int(x),int(y));
    vec4 opix=imageLoad(obstaclesTex, coord);
    return (opix.r<0.1);
}

float readChannel(vec4 pix, int s) {
    if(s==0) return pix.r;
    if(s==1) return pix.g;
    if(s==2) return pix.b;
    if(s==3) return pix.a;
    return 0.0;
}
vec4 writeChannel(vec4 pix,int s,float amt){
    if(s==0) pix.r += amt;
    else if(s==1) pix.g += amt;
    else if(s==2) pix.b += amt;
    else if(s==3) pix.a += amt;
    return pix;
}

float sampleTrail(float x,float y,int s) {
    if(x<0.0||x>=simWidth||y<0.0||y>=simHeight) {
        return 0.0;
    }
    ivec2 coord=ivec2(int(x),int(y));
    vec4 p=imageLoad(trailMap,coord);
    return readChannel(p, s);
}

void main(){
    if(passType==0) {
        // Update Agents
        uint idx=gl_GlobalInvocationID.x;
        if(idx>=gl_NumWorkGroups.x*gl_WorkGroupSize.x) {
            return;
        }
        Agent a=agents[idx];
        // species
        int sI=a.species;
        if(sI<0||sI>=numSpecies) return;

        float spd        = speeds[sI];
        float tSpd       = turnSpeeds[sI];
        float sAng       = sensorAngles[sI];
        float sDist      = sensorDistances[sI];
        float dep        = depositAmounts[sI];

        // Scale deposit to avoid big single-agent blobs
        dep *= depositScaleFactor;  

        // sense
        float leftA = a.angle - sAng;
        float rightA= a.angle + sAng;
        float fwdA  = a.angle;

        float lx=a.x+cos(leftA)*sDist;
        float ly=a.y+sin(leftA)*sDist;
        float rx=a.x+cos(rightA)*sDist;
        float ry=a.y+sin(rightA)*sDist;
        float fx=a.x+cos(fwdA)*sDist;
        float fy=a.y+sin(fwdA)*sDist;

        float lv=sampleTrail(lx,ly,sI);
        float rv=sampleTrail(rx,ry,sI);
        float fv=sampleTrail(fx,fy,sI);

        if(fv>lv && fv>rv) {
            // no turn
        } else if(lv>rv) {
            a.angle -= tSpd;
        } else {
            a.angle += tSpd;
        }

        // random wiggle
        float r=rand(a.seed);
        a.angle += (r-0.5)*randomTurnFactor;

        // move
        float dx=cos(a.angle)*spd;
        float dy=sin(a.angle)*spd;
        float nx=a.x+dx;
        float ny=a.y+dy;

        if(useObstacles) {
            if(isBlocked(nx,ny)) {
                a.angle += 3.14159;
            } else {
                a.x=nx; a.y=ny;
            }
        } else {
            a.x=nx; a.y=ny;
            if(a.x<0.0||a.x>=simWidth||a.y<0.0||a.y>=simHeight){
                if(a.x<0.0) a.x=0.0;
                if(a.x>=simWidth)  a.x=simWidth-1.0;
                if(a.y<0.0) a.y=0.0;
                if(a.y>=simHeight) a.y=simHeight-1.0;
                a.angle+=3.14159;
            }
        }

        // deposit
        ivec2 coord=ivec2(int(a.x),int(a.y));
        vec4 oldPix=imageLoad(trailMap,coord);
        vec4 newPix=writeChannel(oldPix,sI,dep);
        imageStore(trailMap,coord,newPix);

        agents[idx]=a;
    }
    else if(passType==1) {
        // Evap
        uint globalID=gl_GlobalInvocationID.x;
        uint total=uint(simWidth*simHeight);
        if(globalID>=total) return;
        uint y=globalID/uint(simWidth);
        uint x=globalID%uint(simWidth);

        vec4 p=imageLoad(trailMap, ivec2(x,y));
        p*=evaporationFactor;
        imageStore(trailMap, ivec2(x,y), p);
    }
    else if(passType==2) {
        // Blur
        uint globalID=gl_GlobalInvocationID.x;
        uint total=uint(simWidth*simHeight);
        if(globalID>=total) return;
        uint y=globalID/uint(simWidth);
        uint x=globalID%uint(simWidth);

        int rad=blurRadius;
        vec4 sum=vec4(0.0);
        float count=0.0;
        for(int dy=-rad; dy<=rad; dy++){
            for(int dx=-rad; dx<=rad; dx++){
                int nx=int(x)+dx;
                int ny=int(y)+dy;
                if(nx>=0 && nx<int(simWidth) && ny>=0 && ny<int(simHeight)){
                    sum += imageLoad(trailMap, ivec2(nx,ny));
                    count+=1.0;
                }
            }
        }
        vec4 outPix=sum/count;
        imageStore(trailMap, ivec2(x,y), outPix);
    }
}
""";

VERTEX_SHADER_SOURCE = r"""
#version 430
layout(location=0) in vec2 inPos;
out vec2 texCoord;
void main(){
    texCoord = (inPos*0.5)+0.5;
    gl_Position=vec4(inPos, 0,1);
}
""";

FRAGMENT_SHADER_SOURCE = r"""
#version 430
in vec2 texCoord;
out vec4 fragColor;

uniform sampler2D slimeTexture;
uniform float colorMultiplier;
uniform int   colorMode; // 0 => SUM, 1 => RGB, 2 => CUSTOM
uniform vec4  backgroundColor;

void main(){
    vec4 pix=texture(slimeTexture, texCoord);

    if(colorMode==0){
        float val=(pix.r+pix.g+pix.b+pix.a)*0.25*colorMultiplier;
        if(val>1.0) val=1.0;
        fragColor=mix(backgroundColor, vec4(1,1,1,1), val);
    } else if(colorMode==1){
        vec3 c=(pix.rgb)*colorMultiplier;
        c=clamp(c,0.0,1.0);
        fragColor=vec4(c,1.0);
    } else {
        float val=(pix.r+pix.g+pix.b+pix.a)*0.25*colorMultiplier;
        if(val>1.0) val=1.0;
        // e.g. custom bluish
        fragColor=vec4(0.0, val, val*0.5,1.0);
    }
}
""";

def create_fullscreen_quad_vao():
    import numpy as np
    verts = np.array([
        -1.0,-1.0,
         1.0,-1.0,
        -1.0, 1.0,
         1.0, 1.0,
    ], dtype=np.float32)
    vao=glGenVertexArrays(1)
    glBindVertexArray(vao)
    buf=glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, buf)
    glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,0,None)
    glBindBuffer(GL_ARRAY_BUFFER,0)
    glBindVertexArray(0)
    return vao

def main():
    if not glfw.init():
        print("GLFW init failed")
        sys.exit(1)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR,4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR,3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.RESIZABLE,False)

    window=glfw.create_window(config.WINDOW_WIDTH, config.WINDOW_HEIGHT,"Slime GPU Python",None,None)
    if not window:
        print("create window fail")
        glfw.terminate()
        sys.exit(1)

    glfw.make_context_current(window)

    computeShader=compileShader(COMPUTE_SHADER_SOURCE, GL_COMPUTE_SHADER)
    computeProg = compileProgram(computeShader)

    vs=compileShader(VERTEX_SHADER_SOURCE, GL_VERTEX_SHADER)
    fs=compileShader(FRAGMENT_SHADER_SOURCE, GL_FRAGMENT_SHADER)
    renderProg=compileProgram(vs, fs)

    # RGBA32F trail map
    trailTex=glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, trailTex)
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F, config.SIM_WIDTH, config.SIM_HEIGHT,0,GL_RGBA,GL_FLOAT,None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,GL_NEAREST)
    glBindTexture(GL_TEXTURE_2D,0)

    # obstacles
    obstaclesTex=glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, obstaclesTex)
    if config.USE_OBSTACLES:
        img=Image.open(config.OBSTACLE_IMAGE).convert('L')
        arr=np.array(img,dtype=np.uint8)
        glTexImage2D(GL_TEXTURE_2D,0,GL_R8,arr.shape[1],arr.shape[0],0,GL_RED,GL_UNSIGNED_BYTE,arr)
    else:
        arr=np.full((config.SIM_HEIGHT, config.SIM_WIDTH),255,dtype=np.uint8)
        glTexImage2D(GL_TEXTURE_2D,0,GL_R8, config.SIM_WIDTH,config.SIM_HEIGHT,0,GL_RED,GL_UNSIGNED_BYTE,arr)
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST)
    glBindTexture(GL_TEXTURE_2D,0)

    # Clear trail map
    zeroArr=np.zeros((config.SIM_HEIGHT, config.SIM_WIDTH,4),dtype=np.float32)
    glBindTexture(GL_TEXTURE_2D, trailTex)
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0, config.SIM_WIDTH, config.SIM_HEIGHT, GL_RGBA, GL_FLOAT, zeroArr)
    glBindTexture(GL_TEXTURE_2D,0)

    # Agent SSBO
    if config.MULTI_SPECIES:
        totalAgents=sum(config.SPECIES_AGENT_COUNTS)
    else:
        totalAgents=config.NUM_AGENTS

    dtype=[('x','f4'),('y','f4'),('angle','f4'),('seed','f4'),('species','i4')]
    agentData=np.zeros(totalAgents, dtype=dtype)

    if config.MULTI_SPECIES:
        idx=0
        for sI,count in enumerate(config.SPECIES_AGENT_COUNTS):
            for c in range(count):
                agentData[idx]['x']=random.uniform(0, config.SIM_WIDTH)
                agentData[idx]['y']=random.uniform(0, config.SIM_HEIGHT)
                agentData[idx]['angle']=random.uniform(0, math.pi*2)
                if config.USE_RANDOM_SEEDS:
                    agentData[idx]['seed']=random.random()
                else:
                    agentData[idx]['seed']=0.5
                agentData[idx]['species']=sI
                idx+=1
    else:
        for i in range(totalAgents):
            agentData[i]['x']=random.uniform(0, config.SIM_WIDTH)
            agentData[i]['y']=random.uniform(0, config.SIM_HEIGHT)
            agentData[i]['angle']=random.uniform(0,math.pi*2)
            agentData[i]['seed']=random.random() if config.USE_RANDOM_SEEDS else 0.5
            agentData[i]['species']=0

    ssbo=glGenBuffers(1)
    glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssbo)
    glBufferData(GL_SHADER_STORAGE_BUFFER, agentData.nbytes, agentData, GL_DYNAMIC_DRAW)
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER,0, ssbo)
    glBindBuffer(GL_SHADER_STORAGE_BUFFER,0)

    quadVAO=create_fullscreen_quad_vao()

    # compute uniforms
    cPassType=glGetUniformLocation(computeProg,"passType")
    cW=glGetUniformLocation(computeProg,"simWidth")
    cH=glGetUniformLocation(computeProg,"simHeight")
    cObs=glGetUniformLocation(computeProg,"useObstacles")
    cEvap=glGetUniformLocation(computeProg,"evaporationFactor")
    cBlur=glGetUniformLocation(computeProg,"blurRadius")

    cNumSp=glGetUniformLocation(computeProg,"numSpecies")
    cSpds =glGetUniformLocation(computeProg,"speeds")
    cTSpd =glGetUniformLocation(computeProg,"turnSpeeds")
    cSAng =glGetUniformLocation(computeProg,"sensorAngles")
    cSDst =glGetUniformLocation(computeProg,"sensorDistances")
    cDep  =glGetUniformLocation(computeProg,"depositAmounts")
    cRnd  =glGetUniformLocation(computeProg,"randomTurnFactor")

    # new param
    cDepScale=glGetUniformLocation(computeProg,"depositScaleFactor")

    glUseProgram(computeProg)
    glUniform1f(cW, float(config.SIM_WIDTH))
    glUniform1f(cH, float(config.SIM_HEIGHT))
    glUniform1i(cObs, GL_TRUE if config.USE_OBSTACLES else GL_FALSE)
    glUniform1f(cEvap, config.EVAPORATION_FACTOR)
    glUniform1i(cBlur, config.BLUR_RADIUS)
    glUniform1f(cRnd, config.RANDOM_TURN_FACTOR)

    # deposit scale factor
    # If totalAgents=300k but user sets AGENT_DEPOSIT_SCALE=300k,
    # depScaleFactor = (1.0 * base) => for 300k
    # If user sets only 1 agent => deposit scale factor => base*(1/1) => too big?
    # Actually let's do factor = (AGENT_DEPOSIT_SCALE / totalAgents).
    # So if you have fewer agents, each deposit is smaller.
    depositScaleVal = (float(config.AGENT_DEPOSIT_SCALE)/float(totalAgents))
    glUniform1f(cDepScale, depositScaleVal)

    if config.MULTI_SPECIES:
        glUniform1i(cNumSp, config.NUM_SPECIES)
        glUniform1fv(cSpds, config.NUM_SPECIES, np.array(config.SPECIES_SPEEDS, dtype=np.float32))
        glUniform1fv(cTSpd, config.NUM_SPECIES, np.array(config.SPECIES_TURN_SPEEDS,dtype=np.float32))
        anglesInRad = [math.radians(a) for a in config.SPECIES_SENSOR_ANGLES]
        glUniform1fv(cSAng, config.NUM_SPECIES, np.array(anglesInRad, dtype=np.float32))
        glUniform1fv(cSDst, config.NUM_SPECIES, np.array(config.SPECIES_SENSOR_DIST, dtype=np.float32))
        glUniform1fv(cDep,  config.NUM_SPECIES, np.array(config.SPECIES_DEPOSIT_AMOUNTS, dtype=np.float32))
    else:
        glUniform1i(cNumSp, 1)
        glUniform1fv(cSpds, 1, np.array([config.AGENT_SPEED], dtype=np.float32))
        glUniform1fv(cTSpd, 1, np.array([config.TURN_SPEED],  dtype=np.float32))
        glUniform1fv(cSAng, 1, np.array([math.radians(config.SENSOR_ANGLE_DEG)],dtype=np.float32))
        glUniform1fv(cSDst, 1, np.array([config.SENSOR_DISTANCE], dtype=np.float32))
        glUniform1fv(cDep,  1, np.array([config.DEPOSIT_AMOUNT], dtype=np.float32))

    glUseProgram(0)

    # render uniforms
    rTex=glGetUniformLocation(renderProg,"slimeTexture")
    rMul=glGetUniformLocation(renderProg,"colorMultiplier")
    rMod=glGetUniformLocation(renderProg,"colorMode")
    rBG =glGetUniformLocation(renderProg,"backgroundColor")

    if config.MULTI_SPECIES:
        totalAgents=sum(config.SPECIES_AGENT_COUNTS)
    else:
        totalAgents=config.NUM_AGENTS

    groupCountAgents=(totalAgents+255)//256
    totalPix = config.SIM_WIDTH*config.SIM_HEIGHT
    groupCountPixels=(totalPix+255)//256

    lastTime=glfw.get_time()

    while not glfw.window_should_close(window):
        glfw.poll_events()

        # screenshot
        if glfw.get_key(window, config.SCREENSHOT_KEY)==glfw.PRESS:
            take_screenshot(window, config.SCREENSHOT_FILE)

        if config.TARGET_FPS>0:
            now=glfw.get_time()
            dt=now - lastTime
            target=1.0/config.TARGET_FPS
            if dt<target:
                glfw.wait_events_timeout(target-dt)
            lastTime=glfw.get_time()

        # 1) Agent update
        glUseProgram(computeProg)
        glUniform1i(cPassType, 0)
        glBindImageTexture(0, trailTex,0, GL_FALSE,0,GL_READ_WRITE,GL_RGBA32F)
        glBindImageTexture(1, obstaclesTex,0,GL_FALSE,0,GL_READ_ONLY,GL_R8)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER,0, ssbo)

        glDispatchCompute(groupCountAgents,1,1)
        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT|GL_SHADER_STORAGE_BARRIER_BIT)

        # 2) Evap
        glUniform1i(cPassType,1)
        glDispatchCompute(groupCountPixels,1,1)
        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        # 3) Blur pass
        glUniform1i(cPassType,2)
        for _ in range(config.BLUR_PASSES):
            glDispatchCompute(groupCountPixels,1,1)
            glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        # 4) render
        glViewport(0,0, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        bg = config.BACKGROUND_COLOR
        glClearColor(bg[0], bg[1], bg[2], bg[3])
        glClear(GL_COLOR_BUFFER_BIT)

        glUseProgram(renderProg)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, trailTex)
        glUniform1i(rTex,0)

        glUniform1f(rMul, config.COLOR_MULTIPLIER)
        if config.COLOR_MODE=="SUM":
            glUniform1i(rMod,0)
        elif config.COLOR_MODE=="RGB":
            glUniform1i(rMod,1)
        else:
            glUniform1i(rMod,2)

        glUniform4f(rBG,bg[0],bg[1],bg[2],bg[3])

        glBindVertexArray(quadVAO)
        glDrawArrays(GL_TRIANGLE_STRIP,0,4)
        glBindVertexArray(0)

        glfw.swap_buffers(window)

    glDeleteProgram(computeProg)
    glDeleteProgram(renderProg)
    glDeleteBuffers(1,[ssbo])
    glDeleteTextures([trailTex, obstaclesTex])
    glDeleteVertexArrays(1,[quadVAO])

    glfw.destroy_window(window)
    glfw.terminate()

def take_screenshot(window, outPath):
    w,h=glfw.get_framebuffer_size(window)
    data=glReadPixels(0,0,w,h,GL_RGBA,GL_UNSIGNED_BYTE)
    arr=np.frombuffer(data,dtype=np.uint8).reshape((h,w,4))
    arr=np.flip(arr,axis=0)
    img=Image.fromarray(arr,'RGBA')
    img.save(outPath)
    print(f"Screenshot saved to {outPath}")

main()